# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
AGS-Lookup: Amtlicher Gemeindeschlüssel → Gemeinde, Kreis, Bundesland.

Struktur des AGS (8 Stellen): LLKKKGGG
  LL  = Bundesland (01–16)
  KKK = Kreis/Landkreis (001–999)
  GGG = Gemeinde innerhalb des Kreises (001–999)

Bundesland wird aus den ersten zwei Stellen abgeleitet (hardcoded, stabil).
Kreis und Gemeinde werden aus der JSON-Datei geladen, die durch den
Management-Command `python manage.py ags_gemeinden_laden` erzeugt wird.

Ohne diese Datei liefert die Suche nur das Bundesland.
"""
from __future__ import annotations
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BUNDESLAENDER: dict[str, str] = {
    "01": "Schleswig-Holstein",
    "02": "Hamburg",
    "03": "Niedersachsen",
    "04": "Bremen",
    "05": "Nordrhein-Westfalen",
    "06": "Hessen",
    "07": "Rheinland-Pfalz",
    "08": "Baden-Württemberg",
    "09": "Bayern",
    "10": "Saarland",
    "11": "Berlin",
    "12": "Brandenburg",
    "13": "Mecklenburg-Vorpommern",
    "14": "Sachsen",
    "15": "Sachsen-Anhalt",
    "16": "Thüringen",
}

# Pfad zur generierten JSON-Datei (wird durch Management-Command erzeugt)
_JSON_PFAD = Path(__file__).parent / "ags_daten.json"

# Cache: wird beim ersten Zugriff geladen
_cache: dict | None = None


def _lade_cache() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    if _JSON_PFAD.exists():
        try:
            with open(_JSON_PFAD, encoding="utf-8") as f:
                _cache = json.load(f)
            logger.info("AGS-Daten geladen: %d Einträge", len(_cache))
        except Exception as exc:
            logger.warning("AGS-JSON konnte nicht geladen werden: %s", exc)
            _cache = {}
    else:
        _cache = {}
    return _cache


def suche(ags: str) -> dict:
    """
    Gibt {gemeinde, kreis, land} für einen AGS zurück.

    ags muss 8 Stellen haben (führende Nullen).
    Fehlende Werte bleiben leere Strings.
    """
    ags = ags.strip().zfill(8)
    if len(ags) != 8 or not ags.isdigit():
        return {"gemeinde": "", "kreis": "", "land": ""}

    bl_code = ags[:2]
    land = BUNDESLAENDER.get(bl_code, "")

    daten = _lade_cache()
    eintrag = daten.get(ags, {})

    return {
        "gemeinde": eintrag.get("gemeinde", ""),
        "kreis": eintrag.get("kreis", ""),
        "land": eintrag.get("land", land),
    }
