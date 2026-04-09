# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
import logging

from .crypto import SESSION_KEY, clear_session_schluessel, set_session_schluessel

logger = logging.getLogger(__name__)


class SignaturKeyMiddleware:
    """Stellt den Signatur-Entschluesselungsschluessel fuer die Dauer eines Requests bereit."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        dk_hex = None
        try:
            if hasattr(request, "session"):
                dk_hex = request.session.get(SESSION_KEY)
        except Exception:
            pass

        if dk_hex:
            set_session_schluessel(dk_hex)

        try:
            response = self.get_response(request)
        finally:
            clear_session_schluessel()

        return response
