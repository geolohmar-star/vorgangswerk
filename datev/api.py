# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""DATEV HR:Exchange API-Client."""
import requests
from django.utils import timezone
from datetime import timedelta
from . import oauth
from .models import DatevToken

HR_EXCHANGE_BASE = oauth.DATEV_API_BASE + "/hr-exchange/v1"


def _gültiger_token(token: DatevToken) -> str:
    """Gibt einen gültigen Access Token zurück – erneuert bei Bedarf."""
    if token.ist_abgelaufen():
        neue_daten = oauth.erneuere_token(token.refresh_token)
        token.access_token = neue_daten["access_token"]
        if "refresh_token" in neue_daten:
            token.refresh_token = neue_daten["refresh_token"]
        expires_in = neue_daten.get("expires_in", 3600)
        token.expires_at = timezone.now() + timedelta(seconds=int(expires_in))
        token.save(update_fields=["access_token", "refresh_token", "expires_at"])
    return token.access_token


def mitarbeiter_erstellen(token: DatevToken, payload: dict) -> dict:
    """Legt einen neuen Mitarbeiter in DATEV HR:Exchange an."""
    access_token = _gültiger_token(token)
    headers = oauth.api_headers(access_token)
    resp = requests.post(
        f"{HR_EXCHANGE_BASE}/employees",
        json=payload,
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}


def mitarbeiter_abrufen(token: DatevToken, employee_id: str) -> dict:
    """Liest einen Mitarbeiter aus DATEV HR:Exchange."""
    access_token = _gültiger_token(token)
    headers = oauth.api_headers(access_token)
    resp = requests.get(
        f"{HR_EXCHANGE_BASE}/employees/{employee_id}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def mitarbeiter_liste(token: DatevToken) -> list:
    """Listet alle Mitarbeiter aus DATEV HR:Exchange."""
    access_token = _gültiger_token(token)
    headers = oauth.api_headers(access_token)
    resp = requests.get(
        f"{HR_EXCHANGE_BASE}/employees",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# HR:Files
# ---------------------------------------------------------------------------

HR_FILES_BASE = oauth.DATEV_API_BASE + "/hr-files/v2"


def datei_hochladen(token: DatevToken, dateiinhalt: bytes, dateiname: str) -> dict:
    """Lädt eine LODAS ASCII-Datei via HR:Files API hoch."""
    access_token = _gültiger_token(token)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    resp = requests.post(
        f"{HR_FILES_BASE}/upload",
        files={"file": (dateiname, dateiinhalt, "text/plain")},
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json() if resp.content else {}
