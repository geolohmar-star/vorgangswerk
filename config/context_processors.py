# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Globale Template-Variablen fuer Vorgangswerk."""
from django.conf import settings


def vorgangswerk_einstellungen(request):
    """Stellt globale Einstellungen in allen Templates bereit."""
    return {
        "COLLABORA_URL": getattr(settings, "COLLABORA_URL", ""),
        "SIGNME_AKTIV": bool(getattr(settings, "SIGNME_API_KEY", "")),
    }
