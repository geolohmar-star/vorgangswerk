# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""DATEV OAuth2 / OpenID Connect Hilfsfunktionen."""
import hashlib
import secrets
import urllib.parse
from django.conf import settings

DATEV_AUTH_URL = "https://login.datev.de/openidsandbox/authorize"
DATEV_TOKEN_URL = "https://login.datev.de/openidsandbox/token"
DATEV_API_BASE  = "https://sandbox-api.datev.de"

# Produktiv:
# DATEV_AUTH_URL = "https://login.datev.de/openid/authorize"
# DATEV_TOKEN_URL = "https://login.datev.de/openid/token"
# DATEV_API_BASE  = "https://api.datev.de"


def get_client_id() -> str:
    return getattr(settings, "DATEV_CLIENT_ID", "")


def get_client_secret() -> str:
    return getattr(settings, "DATEV_CLIENT_SECRET", "")


def get_redirect_uri() -> str:
    return getattr(settings, "DATEV_REDIRECT_URI",
                   "https://vorgangswerk.georg-klein.com/portal/datev/callback/")


def erzeuge_state() -> str:
    return secrets.token_urlsafe(32)


def erzeuge_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def erzeuge_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    import base64
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def authorization_url(state: str, code_verifier: str) -> str:
    challenge = erzeuge_code_challenge(code_verifier)
    params = {
        "response_type": "code",
        "client_id": get_client_id(),
        "redirect_uri": get_redirect_uri(),
        "scope": "openid profile datev:hr-exchange:employee:read",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return DATEV_AUTH_URL + "?" + urllib.parse.urlencode(params)


def hole_token(code: str, code_verifier: str) -> dict:
    """Tauscht Authorization Code gegen Access + Refresh Token."""
    import requests
    resp = requests.post(DATEV_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_redirect_uri(),
        "client_id": get_client_id(),
        "client_secret": get_client_secret(),
        "code_verifier": code_verifier,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def erneuere_token(refresh_token: str) -> dict:
    """Erneuert Access Token per Refresh Token."""
    import requests
    resp = requests.post(DATEV_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": get_client_id(),
        "client_secret": get_client_secret(),
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def api_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
