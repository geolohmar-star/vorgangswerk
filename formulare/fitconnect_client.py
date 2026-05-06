# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
FIT-Connect Ausgang – OAuth2 + Submission API Client (v2).

Testumgebung:
  Token:      https://auth-testing.fit-connect.fitko.dev/token
  Submission: https://test.fit-connect.fitko.dev/submission-api

Produktion:
  Token:      https://auth.fit-connect.fitko.de/token
  Submission: https://submission-api.fit-connect.fitko.de

Konfiguration via .env:
  FITCONNECT_CLIENT_ID
  FITCONNECT_CLIENT_SECRET
  FITCONNECT_TOKEN_URL      (optional, default = Testing)
  FITCONNECT_SUBMISSION_URL (optional, default = Testing)
"""
import hashlib
import json
import logging
import uuid

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("vorgangswerk.fitconnect")

_CACHE_KEY  = "fitconnect_access_token"
_SCOPE      = ""
_TIMEOUT_S  = 15
_META_SCHEMA = "https://schema.fitko.de/fit-connect/metadata/2.0.0/metadata.schema.json"


class FitConnectConfigError(Exception):
    """Client-ID oder Secret nicht konfiguriert."""


class FitConnectTokenError(Exception):
    """Token konnte nicht geholt werden."""


class FitConnectSubmissionError(Exception):
    """Submission fehlgeschlagen."""


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _credentials() -> tuple[str, str]:
    client_id     = getattr(settings, "FITCONNECT_CLIENT_ID",     "").strip()
    client_secret = getattr(settings, "FITCONNECT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise FitConnectConfigError(
            "FITCONNECT_CLIENT_ID und FITCONNECT_CLIENT_SECRET müssen in .env gesetzt sein."
        )
    return client_id, client_secret


def _submission_base_url() -> str:
    return getattr(
        settings, "FITCONNECT_SUBMISSION_URL",
        "https://test.fit-connect.fitko.dev/submission-api",
    ).rstrip("/")


def _sha512_hex(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


# ---------------------------------------------------------------------------
# Token (Schritt 1)
# ---------------------------------------------------------------------------

def get_token(force_refresh: bool = False) -> str:
    """Gibt einen gültigen Bearer-Token zurück (aus Cache oder frisch vom FITKO-Server)."""
    if not force_refresh:
        cached = cache.get(_CACHE_KEY)
        if cached:
            return cached

    client_id, client_secret = _credentials()
    token_url = getattr(
        settings, "FITCONNECT_TOKEN_URL",
        "https://auth-testing.fit-connect.fitko.dev/token",
    )

    logger.info("FIT-Connect Token anfordern: %s", token_url)
    try:
        body = {
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
        }
        if _SCOPE:
            body["scope"] = _SCOPE
        resp = requests.post(token_url, data=body, timeout=_TIMEOUT_S)
    except requests.RequestException as exc:
        raise FitConnectTokenError(f"Netzwerkfehler beim Token-Abruf: {exc}") from exc

    if resp.status_code != 200:
        raise FitConnectTokenError(
            f"Token-Abruf fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:300]}"
        )

    data       = resp.json()
    token      = data.get("access_token", "")
    expires_in = int(data.get("expires_in", 3600))

    if not token:
        raise FitConnectTokenError(f"Kein access_token in Antwort: {data}")

    cache.set(_CACHE_KEY, token, timeout=max(expires_in - 60, 30))
    logger.info("FIT-Connect Token gespeichert (TTL %ds)", expires_in - 60)
    return token


def token_info() -> dict:
    """Gibt Metadaten des aktuellen Tokens zurück (für Diagnose/Admin)."""
    client_id, _ = _credentials()
    cached = cache.get(_CACHE_KEY)
    return {
        "client_id":      client_id,
        "token_url":      getattr(settings, "FITCONNECT_TOKEN_URL", ""),
        "submission_url": getattr(settings, "FITCONNECT_SUBMISSION_URL", ""),
        "scope":          _SCOPE,
        "token_cached":   bool(cached),
        "token_preview":  (cached[:12] + "…") if cached else None,
    }


# ---------------------------------------------------------------------------
# Destination-Key (v2)
# ---------------------------------------------------------------------------

def _hole_destination_enc_key(destination_id: str, token: str) -> dict:
    """Holt den öffentlichen Verschlüsselungs-JWK der Empfangsbehörde via v2 API."""
    base_url = _submission_base_url()
    headers  = {"Authorization": f"Bearer {token}"}

    # Destination-Objekt holen → encryptionKid ermitteln
    try:
        resp = requests.get(
            f"{base_url}/v2/destinations/{destination_id}",
            headers=headers,
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler bei Destination-Abfrage: {exc}") from exc

    if resp.status_code != 200:
        raise FitConnectSubmissionError(
            f"Destination-Abfrage fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:300]}"
        )

    try:
        dest = resp.json()
    except Exception:
        raise FitConnectSubmissionError(
            f"Destination-Antwort kein gültiges JSON (HTTP {resp.status_code}): {resp.text[:300]}"
        )

    # Keys können direkt eingebettet oder über encryptionKid referenziert sein
    enc_kid = dest.get("encryptionKid") or dest.get("encryptionKeyId")
    keys    = dest.get("destinationPublicKeys") or dest.get("keys") or []

    if keys:
        enc_keys = [k for k in keys if k.get("use") == "enc" or k.get("key_ops") == ["wrapKey"]]
        if enc_kid:
            enc_keys = [k for k in enc_keys if k.get("kid") == enc_kid] or enc_keys
        if enc_keys:
            return enc_keys[0]

    # Fallback: Key über separaten Endpunkt holen
    if enc_kid:
        try:
            resp2 = requests.get(
                f"{base_url}/v2/destinations/{destination_id}/keys/{enc_kid}",
                headers=headers,
                timeout=_TIMEOUT_S,
            )
            if resp2.status_code == 200:
                return resp2.json()
        except requests.RequestException:
            pass

    raise FitConnectSubmissionError(
        f"Kein Verschlüsselungs-Key für Destination {destination_id}. Antwort: {dest}"
    )


# ---------------------------------------------------------------------------
# JWE-Verschlüsselung
# ---------------------------------------------------------------------------

def _jwe_verschluesseln(payload_bytes: bytes, public_jwk: dict, content_type: str = "application/json") -> str:
    """Verschlüsselt Bytes per JWE Compact (RSA-OAEP-256 + A256GCM)."""
    try:
        from jwcrypto import jwk as jk, jwe
    except ImportError as exc:
        raise FitConnectSubmissionError(
            "jwcrypto nicht installiert. Bitte: pip install jwcrypto"
        ) from exc

    key   = jk.JWK(**public_jwk)
    token = jwe.JWE(
        plaintext=payload_bytes,
        protected=json.dumps({
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "kid": public_jwk.get("kid", ""),
            "cty": content_type,
        }),
    )
    token.add_recipient(key)
    return token.serialize(compact=True)


# ---------------------------------------------------------------------------
# Metadaten (Schema 2.0.0)
# ---------------------------------------------------------------------------

def _baue_metadaten(
    daten_json:         bytes,
    anhaenge:           list[dict],  # [{"id": uuid, "filename": str, "mimetype": str, "bytes": bytes, "zweck": str}]
    sitzung,
) -> bytes:
    """Baut den Metadatensatz gemäß FIT-Connect Metadata-Schema 2.0.0."""
    schema_uri = (
        getattr(settings, "VORGANGSWERK_BASE_URL", "https://vorgangswerk.georg-klein.com")
        + "/api/fitconnect/schema/antrag/"
    )

    meta = {
        "$schema": _META_SCHEMA,
        "contentStructure": {
            "data": {
                "submissionSchema": {
                    "schemaUri": schema_uri,
                    "mimeType": "application/json",
                },
                "hash": {
                    "type":    "sha512",
                    "content": _sha512_hex(daten_json),
                },
            },
            "attachments": [
                {
                    "attachmentId": a["id"],
                    "filename":     a["filename"],
                    "mimeType":     a["mimetype"],
                    "purpose":      a.get("zweck", "report"),
                    "description":  a.get("beschreibung", ""),
                    "hash": {
                        "type":    "sha512",
                        "content": _sha512_hex(a["bytes"]),
                    },
                }
                for a in anhaenge
            ],
        },
        "additionalReferenceInfo": {
            "senderReference": sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}",
        },
    }

    email = getattr(sitzung, "email", "") or (sitzung.gesammelte_daten or {}).get("email", "")
    if email:
        meta["replyChannel"] = {"eMail": {"address": email}}

    return json.dumps(meta, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# PDF-Erzeugung
# ---------------------------------------------------------------------------

def _erzeuge_sitzung_pdf(sitzung) -> bytes:
    """Erzeugt das ausgefüllte PDF für eine Sitzung (AcroForm → WeasyPrint-Fallback)."""
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
            daten  = sitzung.gesammelte_daten or {}
            felder = []
            for schritt in sitzung.pfad.schritte.all():
                for feld in schritt.felder():
                    if isinstance(feld, dict) and feld.get("id"):
                        wert = daten.get(feld["id"], "")
                        if wert:
                            felder.append({"label": feld.get("label") or feld["id"], "wert": wert})
            html_str  = render_to_string("formulare/sitzung_pdf.html", {"sitzung": sitzung, "felder": felder})
            pdf_bytes = HTML(string=html_str).write_pdf()
        except Exception as exc:
            logger.error("FIT-Connect PDF (WeasyPrint) fehlgeschlagen: %s", exc)

    if not pdf_bytes:
        raise FitConnectSubmissionError("PDF-Erzeugung für Submission fehlgeschlagen.")
    return pdf_bytes


# ---------------------------------------------------------------------------
# Submission (v2 – 3-Schritt-Ablauf)
# ---------------------------------------------------------------------------

def submit_sitzung(sitzung) -> tuple[str, str]:
    """
    Reicht eine Antragssitzung per FIT-Connect Submission API v2 ein.

    Ablauf:
      1. Token holen
      2. Destination-JWK (enc) holen
      3. PDF erzeugen
      4. POST /v2/submissions  →  submissionId
      5. PUT  /v2/submissions/{id}/attachments/{attachmentId}  (JWE-verschlüsselt)
      6. PUT  /v2/submissions/{id}  mit encryptedMetadata + encryptedData

    Gibt (submission_id, status) zurück.
    """
    destination_id = getattr(sitzung.pfad, "fitconnect_destination_id", "").strip()
    if not destination_id:
        destination_id = getattr(settings, "FITCONNECT_DESTINATION_ID", "").strip()
    if not destination_id:
        raise FitConnectSubmissionError(
            f"Kein FIT-Connect Destination-ID für Pfad '{sitzung.pfad.name}' konfiguriert."
        )

    token    = get_token()
    headers  = {"Authorization": f"Bearer {token}"}
    base_url = _submission_base_url()

    logger.info("FIT-Connect: hole Destination-Key für %s", destination_id)
    enc_key = _hole_destination_enc_key(destination_id, token)

    logger.info("FIT-Connect: erzeuge PDF für Sitzung %s", sitzung.pk)
    pdf_bytes = _erzeuge_sitzung_pdf(sitzung)

    vorgangsnummer  = sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}"
    pdf_attachment_id = str(uuid.uuid4())
    pdf_filename    = f"{vorgangsnummer}.pdf"

    daten_json = json.dumps(sitzung.gesammelte_daten or {}, ensure_ascii=False).encode("utf-8")

    anhaenge = [{
        "id":          pdf_attachment_id,
        "filename":    pdf_filename,
        "mimetype":    "application/pdf",
        "bytes":       pdf_bytes,
        "zweck":       "report",
        "beschreibung": sitzung.pfad.name,
    }]

    # Schritt 4: Submission anlegen
    leika = getattr(sitzung.pfad, "leika_schluessel", "").strip()
    announce_body: dict = {
        "destinationId": destination_id,
        "announcedAttachments": [pdf_attachment_id],
        "publicService": {
            "name":       sitzung.pfad.name or "Antrag",
            "identifier": f"urn:de:fim:leistung:{leika}" if leika else "urn:de:fim:leistung:99010028",
        },
    }

    logger.info("FIT-Connect: POST /v2/submissions")
    try:
        resp = requests.post(
            f"{base_url}/v2/submissions",
            json=announce_body,
            headers={**headers, "Content-Type": "application/json"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler bei Submission-Anlage: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise FitConnectSubmissionError(
            f"Submission anlegen fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
        )

    try:
        sub_data = resp.json()
    except Exception:
        raise FitConnectSubmissionError(
            f"Submissions-Antwort kein gültiges JSON (HTTP {resp.status_code}): {resp.text[:300]}"
        )
    submission_id = sub_data.get("submissionId") or sub_data.get("id")
    if not submission_id:
        raise FitConnectSubmissionError(f"Keine Submission-ID in Antwort: {sub_data}")
    logger.info("FIT-Connect: Submission-ID %s", submission_id)

    # Schritt 5: Anhänge hochladen (je JWE-verschlüsselt)
    for anhang in anhaenge:
        logger.info("FIT-Connect: lade Anhang hoch %s", anhang["filename"])
        jwe_bytes = _jwe_verschluesseln(anhang["bytes"], enc_key, anhang["mimetype"])
        try:
            resp = requests.put(
                f"{base_url}/v2/submissions/{submission_id}/attachments/{anhang['id']}",
                data=jwe_bytes.encode("ascii"),
                headers={**headers, "Content-Type": "application/jose"},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise FitConnectSubmissionError(f"Netzwerkfehler beim Anhang-Upload: {exc}") from exc

        if resp.status_code not in (200, 201, 204):
            raise FitConnectSubmissionError(
                f"Anhang-Upload fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
            )

    # Schritt 6: Metadaten + Fachdaten JWE-verschlüsselt hochladen
    logger.info("FIT-Connect: baue + verschlüssele Metadaten")
    meta_bytes = _baue_metadaten(daten_json, anhaenge, sitzung)
    meta_jwe   = _jwe_verschluesseln(meta_bytes, enc_key, "application/json")
    daten_jwe  = _jwe_verschluesseln(daten_json, enc_key, "application/json")

    logger.info("FIT-Connect: PUT /v2/submissions/%s", submission_id)
    try:
        resp = requests.put(
            f"{base_url}/v2/submissions/{submission_id}",
            json={"encryptedMetadata": meta_jwe, "encryptedData": daten_jwe},
            headers={**headers, "Content-Type": "application/json"},
            timeout=_TIMEOUT_S,
        )
    except requests.RequestException as exc:
        raise FitConnectSubmissionError(f"Netzwerkfehler beim finalen Upload: {exc}") from exc

    if resp.status_code not in (200, 201, 204):
        raise FitConnectSubmissionError(
            f"Finaler Upload fehlgeschlagen: HTTP {resp.status_code} – {resp.text[:400]}"
        )

    status = "submitted"
    try:
        status = resp.json().get("status", "submitted")
    except Exception:
        pass

    logger.info("FIT-Connect Submission erfolgreich: %s (Status: %s)", submission_id, status)
    return submission_id, status


# ---------------------------------------------------------------------------
# Status-Polling (v2)
# ---------------------------------------------------------------------------

def pruefe_submission_status(submission_id: str) -> str:
    """Fragt den Status einer laufenden Submission ab (v2).

    Mögliche Werte: submitted | forwarded | delivered | rejected
    """
    token    = get_token()
    base_url = _submission_base_url()
    try:
        resp = requests.get(
            f"{base_url}/v2/submissions/{submission_id}",
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
