# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Gibt dictionary[key] zurueck (fuer QueryDict und normale Dicts)."""
    if hasattr(dictionary, "get"):
        return dictionary.get(key, "")
    return ""


@register.filter
def split(value, sep=","):
    """Teilt einen String anhand des Trennzeichens."""
    return str(value).split(sep)


@register.filter
def strip(value):
    """Entfernt fuehrendes/abschliessendes Leerzeichen."""
    return str(value).strip()
