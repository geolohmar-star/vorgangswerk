# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: AGS-Gemeindeverzeichnis laden.

Quellen (wählen Sie eine):
  1. --wikidata   : automatischer Download von Wikidata (SPARQL, kein Account nötig)
  2. --datei PFAD : lokale GV100-Datei (.adm oder .zip) vom Destatis
  3. --url URL    : direkte URL zur GV100-ZIP-Datei

Destatis GV100: https://www.destatis.de/DE/Themen/Laender-Regionen/Regionales/
                Gemeindeverzeichnis/Administrativ/Archiv/GV100ADJ/

Nutzung:
    python manage.py ags_gemeinden_laden --wikidata
    python manage.py ags_gemeinden_laden --datei GV100ADJ.zip
    python manage.py ags_gemeinden_laden --url https://...

Das Ergebnis wird als formulare/ags_daten.json gespeichert und von
formulare/ags_lookup.py verwendet.
"""
import json
import time
import urllib.parse
import urllib.request
import zipfile
import io
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from formulare.ags_lookup import BUNDESLAENDER, _JSON_PFAD

_WIKIDATA_URL = "https://query.wikidata.org/sparql"
_USER_AGENT = "VorgangsWerk/1.0 AGS-Lookup (https://github.com/geolohmar-star/vorgangswerk)"


class Command(BaseCommand):
    help = "Lädt das AGS-Gemeindeverzeichnis (Wikidata, GV100 oder URL)"

    def add_arguments(self, parser):
        gruppe = parser.add_mutually_exclusive_group(required=True)
        gruppe.add_argument(
            "--wikidata",
            action="store_true",
            help="Automatischer Download von Wikidata (empfohlen, kein Konto nötig)",
        )
        gruppe.add_argument(
            "--datei",
            type=str,
            metavar="PFAD",
            help="Lokale GV100-Datei (.adm oder .zip mit .adm darin)",
        )
        gruppe.add_argument(
            "--url",
            type=str,
            metavar="URL",
            help="URL zur GV100-ZIP-Datei (direkter Download)",
        )

    def handle(self, *args, **options):
        if options["wikidata"]:
            ergebnis = self._lade_von_wikidata()
        elif options["url"]:
            self.stdout.write(f"Lade GV100 von {options['url']} ...")
            try:
                req = urllib.request.Request(options["url"], headers={"User-Agent": _USER_AGENT})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    rohdaten = resp.read()
            except Exception as exc:
                raise CommandError(f"Download fehlgeschlagen: {exc}") from exc
            inhalt = self._entpacke_zip(rohdaten)
            ergebnis = self._parse_gv100(inhalt)
        else:
            pfad = Path(options["datei"])
            if not pfad.exists():
                raise CommandError(f"Datei nicht gefunden: {pfad}")
            rohdaten = pfad.read_bytes()
            if pfad.suffix.lower() == ".zip":
                inhalt = self._entpacke_zip(rohdaten)
            else:
                inhalt = rohdaten.decode("cp1252", errors="replace")
            ergebnis = self._parse_gv100(inhalt)

        self._speichern(ergebnis)
        self.stdout.write(
            self.style.SUCCESS(
                f"Fertig: {len(ergebnis)} Einträge in {_JSON_PFAD} gespeichert."
            )
        )
        import formulare.ags_lookup as lu
        lu._cache = None

    # -----------------------------------------------------------------------
    # Wikidata
    # -----------------------------------------------------------------------

    def _lade_von_wikidata(self) -> dict:
        """
        Lädt alle deutschen Gemeinden mit AGS, Kreis und Bundesland von Wikidata.
        Verwendet SPARQL mit Paginierung (LIMIT/OFFSET), da Wikidata große
        Anfragen zeitlich begrenzt.
        """
        self.stdout.write("Lade AGS-Daten von Wikidata (kann 1-2 Minuten dauern)...")
        ergebnis = {}
        offset = 0
        limit = 500
        max_seiten = 40  # Sicherheitsgrenze

        sparql_template = """
SELECT ?ags ?gemName ?kreisName ?bundeslandName WHERE {{
  ?gem wdt:P439 ?ags.
  ?gem rdfs:label ?gemName. FILTER(LANG(?gemName) = 'de')
  OPTIONAL {{
    ?gem wdt:P131 ?kreis.
    ?kreis wdt:P31/wdt:P279* wd:Q106658.
    ?kreis rdfs:label ?kreisName. FILTER(LANG(?kreisName) = 'de')
    OPTIONAL {{
      ?kreis wdt:P131 ?bl.
      ?bl wdt:P31 wd:Q1221156.
      ?bl rdfs:label ?bundeslandName. FILTER(LANG(?bundeslandName) = 'de')
    }}
  }}
}} ORDER BY ?ags LIMIT {limit} OFFSET {offset}
"""

        for seite in range(max_seiten):
            query = sparql_template.format(limit=limit, offset=offset)
            params = urllib.parse.urlencode({"query": query, "format": "json"})
            url = f"{_WIKIDATA_URL}?{params}"
            req = urllib.request.Request(url, headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/sparql-results+json",
            })
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    daten = json.loads(resp.read())
            except Exception as exc:
                self.stderr.write(f"  Fehler auf Seite {seite+1}: {exc}")
                break

            treffer = daten.get("results", {}).get("bindings", [])
            if not treffer:
                break

            for b in treffer:
                ags = b.get("ags", {}).get("value", "").strip().zfill(8)
                if len(ags) != 8 or not ags.isdigit():
                    continue
                gemeinde = b.get("gemName", {}).get("value", "")
                kreis    = b.get("kreisName", {}).get("value", "")
                land_raw = b.get("bundeslandName", {}).get("value", "")
                land = land_raw or BUNDESLAENDER.get(ags[:2], "")
                if ags not in ergebnis:  # erste Schreibung gewinnt
                    ergebnis[ags] = {
                        "gemeinde": gemeinde,
                        "kreis": kreis,
                        "land": land,
                    }

            self.stdout.write(
                f"  Seite {seite+1}: {len(treffer)} Einträge, gesamt: {len(ergebnis)}"
            )
            if len(treffer) < limit:
                break
            offset += limit
            time.sleep(1)  # Wikidata-Rate-Limit respektieren

        # Bundesland-Fallback für Einträge ohne Wikidata-Bundesland
        for ags, eintrag in ergebnis.items():
            if not eintrag["land"]:
                eintrag["land"] = BUNDESLAENDER.get(ags[:2], "")

        return ergebnis

    # -----------------------------------------------------------------------
    # GV100 (Destatis)
    # -----------------------------------------------------------------------

    def _entpacke_zip(self, rohdaten: bytes) -> str:
        """Entpackt die erste .adm-Datei aus einem ZIP-Archiv."""
        with zipfile.ZipFile(io.BytesIO(rohdaten)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(".adm") or name.lower().endswith(".txt"):
                    self.stdout.write(f"  Entpacke: {name}")
                    return zf.read(name).decode("cp1252", errors="replace")
        raise CommandError("Keine .adm-Datei im ZIP-Archiv gefunden.")

    def _parse_gv100(self, inhalt: str) -> dict:
        """
        Parst das GV100-Format (Fixed-Width, 307 Zeichen pro Zeile).

        Satzarten:
          10 = Land
          20 = Regierungsbezirk
          30 = Kreis / Landkreis
          40 = Verbandsgemeinde
          50 = Gemeinde
        """
        ergebnis = {}
        aktueller_kreis = ""
        aktuelles_land = ""

        for zeile in inhalt.splitlines():
            if len(zeile) < 22:
                continue

            satzart   = zeile[0:2]
            bl        = zeile[2:4].strip()
            rb        = zeile[4:7].strip()
            kreis_nr  = zeile[7:10].strip()
            gem_nr    = zeile[13:16].strip()
            name      = zeile[22:72].strip()

            if satzart == "10":
                aktuelles_land = BUNDESLAENDER.get(bl, name)
            elif satzart == "30":
                aktueller_kreis = name
            elif satzart == "50":
                ags = f"{bl}{rb}{kreis_nr}{gem_nr}".zfill(8)
                if len(ags) == 8 and ags.isdigit():
                    ergebnis[ags] = {
                        "gemeinde": name,
                        "kreis": aktueller_kreis,
                        "land": aktuelles_land,
                    }

        self.stdout.write(f"  Geparst: {len(ergebnis)} Gemeinden")
        return ergebnis

    def _speichern(self, daten: dict):
        _JSON_PFAD.parent.mkdir(parents=True, exist_ok=True)
        with open(_JSON_PFAD, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, separators=(",", ":"))
        self.stdout.write(f"  Gespeichert: {_JSON_PFAD}")
