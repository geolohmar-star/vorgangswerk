# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
FIT-Connect Ausgang – OAuth2 + Submission API Client.

Testumgebung:
  Token:      https://auth-testing.fit-connect.fitko.dev/token
  Submission: https://submission-api-testing.fit-connect.fitko.dev

Produktion:
  Token:      https://auth.fit-connect.fitko.de/token
  Submission: https://submission-api.fit-connect.fitko.de

Konfiguration via .env:
  FITCONNECT_CLIENT_ID
  FITCONNECT_CLIENT_SECRET
  FITCONNECT_TOKEN_URL      (optional, default = Testing)
  FITCONNECT_SUBMISSION_URL (optional, default = Testing)
"""
import json
import logging

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("vorgangswerk.fitconnect")

_CACHE_KEY   = "fitconnect_access_token"
_SCOPE       = "send:region:de"
_TIMEOUT_S   = 15


class FitConnectConfigError(Exception):
    """Client-ID oder Secret nicht konfiguriert."""


class FitConnectTokenError(Exception):
    """Token konnte nicht geholt werden."""


class FitConnectSubmissionError(Exception):
    """Submission fehlgeschlagen."""


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _credentials() -> tuple[str, str]:
    client_id     = getattr(settings, "FITCONNECT_CLIENT_ID",     "")
    client_secret = getattr(settings, "FITCONNECT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        raise FitConnectConfigError(
            "FITCONNECT_CLIENT_ID und FITCONNECT_CLIENT_SECRET müssen in .env gesetzt sein."
        )
    return client_id, client_secret


def _submission_base_url() -> str:
    return getattr(settings, "FITCONNECT_SUBMISSION_URL",
                   "https://submission-api-testing.fit-connect.fitko.dev")


# ---------------------------------------------------------------------------
# Token (Schritt 1)
# ---------------------------------------------------------------------------

def get_token(force_refresh: bool = False) -> str:
    """Gibt einen gültigen Bearer-Token zurück (aus Cache oder frisch vom FITKO-Server).

    Der Token wird mit 60 Sekunden Puffer vor Ablauf erneuert.
    """
    if not force_refresh:
        cached = cache.get(_CACHE_KEY)
        if cached:
            logger.debug("FIT-Connect Token aus Cache")
            return cached

    client_id, client_secret = _credentials()
    token_url = getattr(settings, "FITCONNECT_TOKEN_URL",
                        "https://auth-testing.fit-connect.fitko.dev/token")

    logger.info("FIT-Connect Token anfordern: %s", token_url)
    try:
        resp = requests.post(
            token_url,
            data={
                "grant_type":    "client_credentials",
                "client_id":     client_id,
                "client_secret": client_secret,
                "scope":         _SCOPE,
            },
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectTokenError(f"Netzwerkfehler beim Token-Abruf: {exc}") from exc

    if resp.status_code != 200:
        raise FitConnectTokenError(
            f"Token-Abruf fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:300]}"
        )

    data = resp.json()
    token      = data.get("access_token", "")
    expires_in = int(data.get("expires_in", 3600))

    if not token:
        raise FitConnectTokenError(f"Kein access_token in Antwort: {data}")

    ttl = max(expires_in - 60, 30)
    cache.set(_CACHE_KEY, token, timeout=ttl)
    logger.info("FIT-Connect Token gespeichert (TTL %ds)", ttl)
    return token


def token_info() -> dict:
    """Gibt Metadaten des aktuellen Tokens zurück (für Diagnose/Admin)."""
    client_id, _ = _credentials()
    token_url    = getattr(settings, "FITCONNECT_TOKEN_URL", "")
    sub_url      = getattr(settings, "FITCONNECT_SUBMISSION_URL", "")
    cached       = cache.get(_CACHE_KEY)
    return {
        "client_id":      client_id,
        "token_url":      token_url,
        "submission_url": sub_url,
        "scope":          _SCOPE,
        "token_cached":   bool(cached),
        "token_preview":  (cached[:12] + "…") if cached else None,
    }


# ---------------------------------------------------------------------------
# Destination-Key & JWE-Verschlüsselung (Schritt 3)
# ---------------------------------------------------------------------------

def _hole_destination_enc_key(destination_id: str, token: str) -> dict:
    """Holt den öffentlichen JWK (use=enc) der Empfangsbehörde."""
    url = f"{_submission_base_url()}/v1/destinations/{destination_id}"
    try:
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler bei Destination-Abfrage: {exc}") from exc

    if resp.status_code != 200:
        raise FitConnectSubmissionError(
            f"Destination-Abfrage fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:300]}"
        )

    data = resp.json()
    keys = data.get("destinationPublicKeys", [])
    enc_keys = [k for k in keys if k.get("use") == "enc"]
    if not enc_keys:
        raise FitConnectSubmissionError(
            f"Kein Verschlüsselungs-Key für Destination {destination_id}. Antwort: {data}"
        )
    return enc_keys[0]


def _jwe_verschluesseln(payload_bytes: bytes, public_jwk: dict) -> str:
    """Verschlüsselt Bytes per JWE (RSA-OAEP-256 + A256GCM), gibt compact token zurück."""
    try:
        from jwcrypto import jwk as jk, jwe
    except ImportError as exc:
        raise FitConnectSubmissionError(
            "jwcrypto nicht installiert. Bitte: pip install jwcrypto"
        ) from exc

    key = jk.JWK(**public_jwk)
    token = jwe.JWE(
        plaintext=payload_bytes,
        protected=json.dumps({
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "kid": public_jwk.get("kid", ""),
        }),
    )
    token.add_recipient(key)
    return token.serialize(compact=True)


# ---------------------------------------------------------------------------
# PDF-Erzeugung (intern)
# ---------------------------------------------------------------------------

def _erzeuge_sitzung_pdf(sitzung) -> bytes:
    """Erzeugt das ausgefüllte PDF für eine Sitzung.

    Versucht zuerst AcroForm-Filling mit dem Original-PDF.
    Fallback: WeasyPrint-HTML-Zusammenfassung.
    """
    pdf_bytes = None

    try:
        from portal.models import FormularAnalyse
        from portal.pdf_fill import fuelle_acroform
        analyse = (
            FormularAnalyse.objects
            .filter(importierter_pfad_pk=sitzung.pfad.pk)
            .order_by("-erstellt_am")
            .first()
        )
        if analyse and (analyse.pdf_original or analyse.pdf_inhalt):
            raw = bytes(analyse.pdf_original if analyse.pdf_original else analyse.pdf_inhalt)
            pdf_bytes = fuelle_acroform(
                raw,
                sitzung.pfad.schritte.all(),
                sitzung.gesammelte_daten or {},
                pfad_name=sitzung.pfad.name,
                vorgangsnummer=sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}",
            )
    except Exception as exc:
        logger.warning("FIT-Connect PDF (AcroForm) fehlgeschlagen, Fallback: %s", exc)

    if not pdf_bytes:
        try:
            from weasyprint import HTML
            from django.template.loader import render_to_string
            daten = sitzung.gesammelte_daten or {}
            felder = []
            for schritt in sitzung.pfad.schritte.all():
                for feld in schritt.felder():
                    if isinstance(feld, dict) and feld.get("id"):
                        wert = daten.get(feld["id"], "")
                        if wert:
                            felder.append({"label": feld.get("label") or feld["id"], "wert": wert})
            html_str = render_to_string("formulare/sitzung_pdf.html", {
                "sitzung": sitzung,
                "felder":  felder,
            })
            pdf_bytes = HTML(string=html_str).write_pdf()
        except Exception as exc:
            logger.error("FIT-Connect PDF (WeasyPrint) fehlgeschlagen: %s", exc)

    if not pdf_bytes:
        raise FitConnectSubmissionError("PDF-Erzeugung für Submission fehlgeschlagen.")

    return pdf_bytes


# ---------------------------------------------------------------------------
# Submission (Schritt 2 + 3)
# ---------------------------------------------------------------------------

def submit_sitzung(sitzung) -> str:
    """
    Reicht eine Antragssitzung per FIT-Connect Submission API ein.

    Ablauf:
      1. Token holen
      2. Destination-Key (JWK) holen
      3. PDF erzeugen
      4. POST /v1/submissions → Submission-ID
      5. PDF JWE-verschlüsselt hochladen
      6. Antragsdaten JSON JWE-verschlüsselt hochladen
      7. POST /v1/submissions/{id}/submit → finalisieren

    Gibt die Submission-ID (UUID) zurück.
    Wirft FitConnectSubmissionError bei Fehlern.
    """
    destination_id = getattr(sitzung.pfad, "fitconnect_destination_id", "").strip()
    if not destination_id:
        raise FitConnectSubmissionError(
            f"Kein FIT-Connect Destination-ID für Pfad '{sitzung.pfad.name}' konfiguriert. "
            "Bitte im Formular-Editor unter Pfad-Einstellungen eintragen."
        )

    token = get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}
    base_url = _submission_base_url()

    # Destination-Key für JWE holen
    logger.info("FIT-Connect: hole Destination-Key für %s", destination_id)
    enc_key = _hole_destination_enc_key(destination_id, token)

    # PDF erzeugen
    logger.info("FIT-Connect: erzeuge PDF für Sitzung %s", sitzung.pk)
    pdf_bytes = _erzeuge_sitzung_pdf(sitzung)

    vorgangsnummer = sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}"
    leika = getattr(sitzung.pfad, "leika_schluessel", "").strip()

    # Submission anlegen
    announce_body: dict = {
        "destinationId": destination_id,
        "announcedAttachments": [
            {
                "filename": f"{vorgangsnummer}.pdf",
                "mimeType": "application/pdf",
                "description": sitzung.pfad.name,
            }
        ],
    }
    if leika:
        announce_body["serviceType"] = {
            "name": sitzung.pfad.name,
            "identifier": f"urn:de:fim:leika:leistung:{leika}",
        }

    logger.info("FIT-Connect: POST /v1/submissions")
    try:
        resp = requests.post(
            f"{base_url}/v1/submissions",
            json=announce_body,
            headers={**auth_headers, "Content-Type": "application/json"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler bei Submission-Anlage: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise FitConnectSubmissionError(
            f"Submission anlegen fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
        )

    sub_data = resp.json()
    submission_id = sub_data.get("submissionId") or sub_data.get("id")
    attachment_ids: dict = sub_data.get("attachmentIds", {})

    if not submission_id:
        raise FitConnectSubmissionError(f"Keine Submission-ID in Antwort: {sub_data}")

    logger.info("FIT-Connect: Submission-ID %s", submission_id)

    # PDF hochladen (JWE-verschlüsselt)
    pdf_filename = f"{vorgangsnummer}.pdf"
    attachment_id = attachment_ids.get(pdf_filename)
    if attachment_id:
        logger.info("FIT-Connect: verschlüssele + lade PDF hoch")
        pdf_jwe = _jwe_verschluesseln(pdf_bytes, enc_key)
        try:
            resp = requests.put(
                f"{base_url}/v1/submissions/{submission_id}/attachments/{attachment_id}",
                data=pdf_jwe.encode("ascii"),
                headers={**auth_headers, "Content-Type": "application/jose"},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise FitConnectSubmissionError(f"Netzwerkfehler beim PDF-Upload: {exc}") from exc

        if resp.status_code not in (200, 201, 204):
            raise FitConnectSubmissionError(
                f"PDF-Upload fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
            )
    else:
        logger.warning("FIT-Connect: kein Attachment-Slot für '%s' – überspringe PDF", pdf_filename)

    # Antragsdaten hochladen (JWE-verschlüsselt)
    logger.info("FIT-Connect: verschlüssele + lade Antragsdaten hoch")
    daten_json = json.dumps(sitzung.gesammelte_daten or {}, ensure_ascii=False).encode("utf-8")
    daten_jwe = _jwe_verschluesseln(daten_json, enc_key)
    try:
        resp = requests.put(
            f"{base_url}/v1/submissions/{submission_id}/data",
            data=daten_jwe.encode("ascii"),
            headers={**auth_headers, "Content-Type": "application/jose"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler beim Daten-Upload: {exc}") from exc

    if resp.status_code not in (200, 201, 204):
        raise FitConnectSubmissionError(
            f"Daten-Upload fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
        )

    # Submission finalisieren
    logger.info("FIT-Connect: POST /v1/submissions/%s/submit", submission_id)
    try:
        resp = requests.post(
            f"{base_url}/v1/submissions/{submission_id}/submit",
            headers={**auth_headers, "Content-Type": "application/json"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler beim Submit: {exc}") from exc

    if resp.status_code not in (200, 201, 204):
        raise FitConnectSubmissionError(
            f"Submit fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
        )

    status = "queued"
    try:
        status = resp.json().get("status", "queued")
    except Exception:
        pass

    logger.info("FIT-Connect Submission erfolgreich: %s (Status: %s)", submission_id, status)
    return submission_id, status


# ---------------------------------------------------------------------------
# Status-Polling (Schritt 4 – Vorbereitung)
# ---------------------------------------------------------------------------

def pruefe_submission_status(submission_id: str) -> str:
    """Fragt den Status einer laufenden Submission ab.

    Gibt einen der FITKO-Status zurück: queued | forwarded | delivered | rejected
    """
    token = get_token()
    base_url = _submission_base_url()
    try:
        resp = requests.get(
            f"{base_url}/v1/submissions/{submission_id}/status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler beim Status-Abruf: {exc}") from exc

    if resp.status_code != 200:
        raise FitConnectSubmissionError(
            f"Status-Abruf fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:300]}"
        )

    return resp.json().get("status", "unbekannt")
