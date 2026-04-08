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


@register.filter
def opt_label(opt):
    """Gibt den Anzeigetext einer Option zurueck (vor dem | oder ganzer String)."""
    return str(opt).split("|")[0].strip()


@register.filter
def opt_value(opt):
    """Gibt den Wert einer Option zurueck (nach dem | oder Anzeigetext)."""
    parts = str(opt).split("|", 1)
    return parts[1].strip() if len(parts) > 1 else parts[0].strip()
