# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Webhook-Zustellung fuer die Formularschnittstelle.

Ereignisse:
  antrag.eingereicht     – AntrSitzung abgeschlossen
  workflow.abgeschlossen – WorkflowInstance abgeschlossen
  task.abgeschlossen     – WorkflowTask erledigt

Payload ist FIM-konform: Felder mit fim_id werden separat ausgewiesen.
Signierung: HMAC-SHA256 im Header X-Webhook-Signature (hex).
"""
import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_VERSUCHE = 3
TIMEOUT = 10  # Sekunden


# ---------------------------------------------------------------------------
# Payload-Bausteine
# ---------------------------------------------------------------------------

def _base_url() -> str:
    return getattr(settings, "VORGANGSWERK_BASE_URL", "").rstrip("/")


def _antragsteller_payload(sitzung) -> dict:
    if sitzung.user:
        return {
            "typ": "benutzer",
            "name": sitzung.user.get_full_name() or sitzung.user.username,
            "email": sitzung.user.email or "",
            "username": sitzung.user.username,
        }
    elif sitzung.email_anonym:
        return {"typ": "anonym", "email": sitzung.email_anonym}
    return {"typ": "anonym"}


def _felder_payload(sitzung) -> dict:
    """Gibt gesammelte Daten mit FIM-IDs aus."""
    daten = sitzung.gesammelte_daten or {}
    fim_map: dict[str, str] = {}
    label_map: dict[str, str] = {}
    for schritt in sitzung.pfad.schritte.all():
        for f in (schritt.felder_json or []):
            fid = f.get("id", "")
            if fid:
                label_map[fid] = f.get("label", fid)
                if f.get("fim_id"):
                    fim_map[fid] = f["fim_id"]
    result = {}
    for k, v in daten.items():
        eintrag = {"wert": v, "bezeichnung": label_map.get(k, k)}
        if k in fim_map:
            eintrag["fim_id"] = fim_map[k]
        result[k] = eintrag
    return result


def _dokumente_payload(sitzung) -> list:
    base = _base_url()
    return [
        {
            "feld_id": d.feld_id,
            "name": d.dateiname,
            "mime_type": d.mime_type,
            "url": f"{base}/formulare/datei/{d.pk}/",
        }
        for d in sitzung.dateien.all()
    ]


def _sitzung_payload(sitzung, ereignis: str) -> dict:
    base = _base_url()
    tracking = (
        f"{base}/vorgang/{sitzung.vorgangsnummer}/?token={sitzung.tracking_token}"
        if sitzung.tracking_token else ""
    )
    return {
        "ereignis": ereignis,
        "zeitstempel": timezone.now().isoformat(),
        "vorgangsnummer": sitzung.vorgangsnummer or "",
        "pfad": {
            "name": sitzung.pfad.name,
            "kuerzel": sitzung.pfad.kuerzel or "",
            "leika_schluessel": getattr(sitzung.pfad, "leika_schluessel", "") or "",
        },
        "antragsteller": _antragsteller_payload(sitzung),
        "felder": _felder_payload(sitzung),
        "dokumente": _dokumente_payload(sitzung),
        "tracking_url": tracking,
    }


def _workflow_payload(instanz, ereignis: str) -> dict:
    payload: dict = {
        "ereignis": ereignis,
        "zeitstempel": timezone.now().isoformat(),
        "workflow": {
            "name": instanz.template.name,
            "status": instanz.status,
            "fortschritt": instanz.fortschritt,
        },
    }
    # Sitzung anhängen wenn vorhanden
    try:
        from formulare.models import AntrSitzung
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(AntrSitzung)
        if instanz.content_type == ct:
            sitzung = AntrSitzung.objects.filter(pk=instanz.object_id).first()
            if sitzung:
                payload["vorgangsnummer"] = sitzung.vorgangsnummer or ""
                payload["antragsteller"] = _antragsteller_payload(sitzung)
    except Exception:
        pass
    return payload


# ---------------------------------------------------------------------------
# Signierung
# ---------------------------------------------------------------------------

def _signiere(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Zustellung
# ---------------------------------------------------------------------------

def _zustellen_einmal(konfig, payload: dict) -> tuple[bool, int | None, str]:
    """Liefert (ok, status_code, fehler)."""
    body = json.dumps(payload, ensure_ascii=False).encode()
    sig = _signiere(body, konfig.secret)
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Webhook-Ereignis": payload.get("ereignis", ""),
        "X-Webhook-Signature": f"sha256={sig}",
        "User-Agent": "Vorgangswerk-Webhook/1.0",
    }
    try:
        r = requests.post(konfig.url, data=body, headers=headers, timeout=TIMEOUT)
        ok = 200 <= r.status_code < 300
        return ok, r.status_code, "" if ok else f"HTTP {r.status_code}"
    except Exception as e:
        return False, None, str(e)


def zustellen(konfig, payload: dict, ereignis: str) -> None:
    """Zustellung mit Retry und Protokoll."""
    from .models import WebhookZustellung  # Import hier wegen zirkulaerer Imports
    zustellung = WebhookZustellung.objects.create(
        konfiguration=konfig,
        ereignis=ereignis,
        payload_json=payload,
    )
    for versuch in range(1, MAX_VERSUCHE + 1):
        ok, status_code, fehler = _zustellen_einmal(konfig, payload)
        zustellung.versuche = versuch
        zustellung.letzter_status_code = status_code
        if ok:
            zustellung.zugestellt_am = timezone.now()
            zustellung.fehler = ""
            zustellung.save(update_fields=["versuche", "letzter_status_code", "zugestellt_am", "fehler"])
            logger.info("Webhook %s → %s: OK (%s)", ereignis, konfig.url, status_code)
            return
        zustellung.fehler = fehler
        zustellung.save(update_fields=["versuche", "letzter_status_code", "fehler"])
        logger.warning("Webhook %s → %s Versuch %d fehlgeschlagen: %s", ereignis, konfig.url, versuch, fehler)
    logger.error("Webhook %s → %s: %d Versuche erschöpft", ereignis, konfig.url, MAX_VERSUCHE)


# ---------------------------------------------------------------------------
# Öffentliche Trigger
# ---------------------------------------------------------------------------

def trigger_antrag_eingereicht(sitzung) -> None:
    """Wird in AntrSitzung.abschliessen() aufgerufen."""
    from .models import WebhookKonfiguration
    ereignis = "antrag.eingereicht"
    konfigs = WebhookKonfiguration.objects.filter(
        aktiv=True,
        ereignisse__contains=ereignis,
    ).filter(
        models_filter_pfad(sitzung.pfad_id)
    )
    if not konfigs.exists():
        return
    payload = _sitzung_payload(sitzung, ereignis)
    for k in konfigs:
        try:
            zustellen(k, payload, ereignis)
        except Exception:
            logger.exception("Webhook-Trigger fehlgeschlagen für %s", k.url)


def trigger_workflow_abgeschlossen(instanz) -> None:
    """Wird in WorkflowEngine._benachrichtige_abschluss() aufgerufen."""
    from .models import WebhookKonfiguration
    ereignis = "workflow.abgeschlossen"
    # Pfad aus Sitzung ermitteln
    pfad_id = _pfad_id_aus_instanz(instanz)
    konfigs = WebhookKonfiguration.objects.filter(
        aktiv=True,
        ereignisse__contains=ereignis,
    ).filter(models_filter_pfad(pfad_id))
    if not konfigs.exists():
        return
    payload = _workflow_payload(instanz, ereignis)
    for k in konfigs:
        try:
            zustellen(k, payload, ereignis)
        except Exception:
            logger.exception("Webhook-Trigger fehlgeschlagen für %s", k.url)


def trigger_task_abgeschlossen(task) -> None:
    """Wird in WorkflowEngine.task_abschliessen() aufgerufen."""
    from .models import WebhookKonfiguration
    ereignis = "task.abgeschlossen"
    pfad_id = _pfad_id_aus_instanz(task.instance)
    konfigs = WebhookKonfiguration.objects.filter(
        aktiv=True,
        ereignisse__contains=ereignis,
    ).filter(models_filter_pfad(pfad_id))
    if not konfigs.exists():
        return
    payload = _workflow_payload(task.instance, ereignis)
    payload["task"] = {
        "titel": task.step.titel,
        "entscheidung": task.entscheidung or "",
        "kommentar": task.kommentar or "",
        "erledigt_am": task.erledigt_am.isoformat() if task.erledigt_am else "",
    }
    for k in konfigs:
        try:
            zustellen(k, payload, ereignis)
        except Exception:
            logger.exception("Webhook-Trigger fehlgeschlagen für %s", k.url)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def models_filter_pfad(pfad_id):
    """Q-Filter: Konfig gilt global (pfad=None) oder für diesen Pfad."""
    from django.db.models import Q
    return Q(pfad__isnull=True) | Q(pfad_id=pfad_id)


def _pfad_id_aus_instanz(instanz) -> int | None:
    try:
        from formulare.models import AntrSitzung
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(AntrSitzung)
        if instanz.content_type == ct:
            s = AntrSitzung.objects.filter(pk=instanz.object_id).values_list("pfad_id", flat=True).first()
            return s
    except Exception:
        pass
    return None
