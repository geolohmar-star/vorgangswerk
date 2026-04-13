# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(is_safe=True)
def safe_html(value):
    """
    Bereinigt HTML auf eine Zulässigkeitsliste (lxml).
    Erlaubt: b, i, u, strong, em, p, br, ul, ol, li, a (href, target),
             h3–h6, blockquote, code, pre.
    Entfernt: script, style, on*-Attribute und alle nicht-erlaubten Tags.
    """
    if not value:
        return ""
    try:
        from lxml.html.clean import Cleaner
        cleaner = Cleaner(
            allow_tags=[
                "b", "i", "u", "strong", "em", "p", "br",
                "ul", "ol", "li", "a", "h3", "h4", "h5", "h6",
                "blockquote", "code", "pre", "span", "div",
            ],
            safe_attrs_only=True,
            safe_attrs={"href", "target", "rel", "class"},
            remove_unknown_tags=False,
            scripts=True,
            javascript=True,
            style=True,
            links=False,
            meta=True,
            page_structure=True,
            processing_instructions=True,
            embedded=True,
            frames=True,
            forms=True,
            annoying_tags=True,
        )
        return mark_safe(cleaner.clean_html(str(value)))
    except Exception:
        from django.utils.html import escape
        return escape(value)


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
