# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: Musterpfad "Kanalanschluss – Genehmigung" importieren.

Basiert auf Formular Gemeindewerke Much – Entsorgungsbetrieb.
Nutzung:
    python manage.py import_kanalanschluss
    python manage.py import_kanalanschluss --replace
"""
from django.core.management.base import BaseCommand
from formulare.models import AntrPfad, AntrSchritt, AntrTransition

PFAD_NAME = "Kanalanschluss – Genehmigung"


class Command(BaseCommand):
    help = "Importiert den Musterpfad 'Kanalanschluss – Genehmigung'"

    def add_arguments(self, parser):
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **options):
        if options["replace"]:
            AntrPfad.objects.filter(name=PFAD_NAME).delete()

        pfad = AntrPfad.objects.create(
            name=PFAD_NAME,
            beschreibung=(
                "Antrag auf Erteilung einer Genehmigung zum Anschluss an den gemeindlichen "
                "Kanal (Regen-, Schmutz- oder Mischwasser). Gemeindewerke Much."
            ),
            aktiv=True,
            oeffentlich=True,
            kuerzel="KAN",
            leika_schluessel="",
        )

        schritte_def = [

            # ----------------------------------------------------------------
            # s01 – Antragsteller
            # ----------------------------------------------------------------
            dict(node_id="s01", titel="Antragsteller",
                 ist_start=True, ist_ende=False, pos_x=300, pos_y=80,
                 felder_json=[
                     {"id": "name",      "typ": "text",    "label": "Name des Antragstellers", "pflicht": True,  "fim_id": "F60000004"},
                     {"id": "strasse",   "typ": "text",    "label": "Straße, Haus-Nr.",        "pflicht": True,  "fim_id": "F60000022"},
                     {"id": "plz",       "typ": "plz",     "label": "Postleitzahl",            "pflicht": True,  "fim_id": "F60000024"},
                     {"id": "wohnort",   "typ": "text",    "label": "Wohnort",                 "pflicht": True,  "fim_id": "F60000025"},
                     {"id": "telefon",   "typ": "telefon", "label": "Telefonnummer",           "pflicht": True,  "fim_id": "F60000031"},
                     {"id": "email",     "typ": "email",   "label": "E-Mail",                  "pflicht": False, "fim_id": "F60000030"},
                 ]),

            # ----------------------------------------------------------------
            # s02 – Grundstück & Kanalart
            # ----------------------------------------------------------------
            dict(node_id="s02", titel="Grundstück & Kanalart",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=230,
                 felder_json=[
                     {"id": "abschnitt_kanal",   "typ": "abschnitt", "text": "Art des Kanalanschlusses"},
                     {"id": "kanalart",           "typ": "checkboxen","label": "Anschluss an",  "pflicht": True,
                      "optionen": ["Regenwasserkanal", "Schmutzwasserkanal", "Mischwasserkanal"]},
                     {"id": "abschnitt_grundstueck","typ": "abschnitt","text": "Angaben zum Grundstück"},
                     {"id": "gemarkung",          "typ": "text",    "label": "Gemarkung",        "pflicht": True},
                     {"id": "flur",               "typ": "text",    "label": "Flur",             "pflicht": True},
                     {"id": "flurstueck_nr",      "typ": "text",    "label": "Flurstück-Nr.",    "pflicht": True},
                     {"id": "grundstueck_strasse","typ": "text",    "label": "Straße, Haus-Nr. (Grundstück)", "pflicht": True},
                     {"id": "eigentuemer",        "typ": "text",    "label": "Eigentümer",       "pflicht": True},
                     {"id": "bebauungsart",        "typ": "radio",   "label": "Bebauungsart",    "pflicht": True,
                      "optionen": ["Neubau", "vorhandene Bebauung", "Änderung (Anschluss vorhanden)"]},
                 ]),

            # ----------------------------------------------------------------
            # s03 – Grundstücksnutzung
            # ----------------------------------------------------------------
            dict(node_id="s03", titel="Grundstücksnutzung",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=380,
                 felder_json=[
                     {"id": "nutzung", "typ": "radio", "label": "Das Grundstück wird genutzt", "pflicht": True,
                      "optionen": [
                          "ausschließlich zu Wohnzwecken",
                          "ausschließlich zu gewerblichen Zwecken",
                          "sowohl zu gewerblichen als auch zu Wohnzwecken",
                      ]},
                     {"id": "anzahl_wohneinheiten", "typ": "zahl", "label": "Anzahl der Wohneinheiten",
                      "pflicht": False,
                      "hilfetext": "Nur ausfüllen bei Wohnnutzung"},
                 ]),

            # ----------------------------------------------------------------
            # s03b – Gewerbedetails (NUR bei gewerblicher Nutzung)
            # ----------------------------------------------------------------
            dict(node_id="s03b", titel="Gewerbliche Nutzung – Details",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=380,
                 felder_json=[
                     {"id": "gewerbe_nutzung", "typ": "text",    "label": "Art der gewerblichen Nutzung", "pflicht": True},
                     {"id": "gewerbe_abwasser","typ": "mehrzeil","label": "Art und Menge des voraussichtlich anfallenden Abwassers",
                      "pflicht": True,
                      "hilfetext": "Gemäß Entwässerungssatzung bei überwiegend gewerblicher Nutzung erforderlich"},
                 ]),

            # ----------------------------------------------------------------
            # s04 – Besondere Einrichtungen
            # ----------------------------------------------------------------
            dict(node_id="s04", titel="Besondere Einrichtungen auf dem Grundstück",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=530,
                 felder_json=[
                     {"id": "hinweis_einrichtungen", "typ": "textblock",
                      "text": "Bitte angeben welche besonderen Einrichtungen auf dem Grundstück vorhanden sind."},
                     {"id": "benzinabscheider",       "typ": "bool", "label": "Benzinabscheider"},
                     {"id": "benzinabscheider_anz",   "typ": "zahl", "label": "Anzahl Benzinabscheider", "pflicht": False},
                     {"id": "oelsperre",              "typ": "bool", "label": "Ölsperre(n)"},
                     {"id": "oelsperre_anz",          "typ": "zahl", "label": "Anzahl Ölsperren",        "pflicht": False},
                     {"id": "schwimmbad",             "typ": "bool", "label": "Schwimmbad"},
                     {"id": "regen_grundwasser",      "typ": "bool", "label": "Regen- oder Grundwassernutzung"},
                     {"id": "sonstige_einrichtungen", "typ": "text", "label": "Sonstige Einrichtungen",  "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s04b – Regenwassernutzung Details (NUR wenn vorhanden)
            # ----------------------------------------------------------------
            dict(node_id="s04b", titel="Regen-/Grundwassernutzung – Details",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=530,
                 felder_json=[
                     {"id": "regen_in_kanal",    "typ": "radio", "label": "Soll dieses Wasser teilweise in den Kanal geleitet werden? (z.B. Toilettenspülung, Waschmaschinen)",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "regen_messeinrichtung","typ": "radio","label": "Wird die der Brauchwasseranlage zugeführte Wassermenge über eine Messeinrichtung ermittelt?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                 ]),

            # ----------------------------------------------------------------
            # s05 – Rechtliche Hinweise & Anlagen
            # ----------------------------------------------------------------
            dict(node_id="s05", titel="Rechtliche Hinweise & beizufügende Unterlagen",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=680,
                 felder_json=[
                     {"id": "hinweise_text", "typ": "textblock", "text": (
                         "Mir ist bekannt:\n"
                         "• Prüfschacht (min. DN 800) ist unmittelbar an der Grundstücksgrenze zu errichten.\n"
                         "• Kanalnutzung erst nach vorheriger Abnahme durch die Gemeinde (Anmeldung min. 3 Werktage vorher: 02245/6839 oder 02245/6829).\n"
                         "• Bei Abweichung von der genehmigten Ausführungsart ist eine Nachtragsgenehmigung einzuholen.\n"
                         "• Rückstausicherung gemäß § 3 Abs. 4 Entwässerungssatzung ist Pflicht des Eigentümers.\n"
                         "• Keller-/Hausdrainage und Grund-/Brunnenwasser dürfen nicht angeschlossen werden.\n"
                         "• Anschlussleitung ist frostsicher zu verlegen."
                     )},
                     {"id": "anlage_lageplan",     "typ": "bool", "label": "Lageplan im Maßstab 1:250, DIN A3 liegt bei (2-fach)"},
                     {"id": "anlage_beschreibung", "typ": "bool", "label": "Beschreibung der geplanten Entwässerungsanlage liegt bei (2-fach)"},
                     {"id": "anlage_grundriss",    "typ": "bool", "label": "Grundriss des Kellers (1:100) mit Grundleitung liegt bei (2-fach)"},
                     {"id": "anlage_gewerbe",      "typ": "bool", "label": "Betriebsbeschreibung mit Abwassermengenangabe liegt bei – nur bei Gewerbe (2-fach)",
                      "pflicht": False},
                     {"id": "einwilligung", "typ": "einwilligung",
                      "text": "Ich bestätige die Kenntnisnahme der genannten Bedingungen und versichere die Richtigkeit meiner Angaben.",
                      "pflicht": True},
                 ]),

            # ----------------------------------------------------------------
            # s06 – Unterschrift (ENDE)
            # ----------------------------------------------------------------
            dict(node_id="s06", titel="Ort, Datum & Unterschrift",
                 ist_start=False, ist_ende=True, pos_x=300, pos_y=830,
                 felder_json=[
                     {"id": "ort",          "typ": "text",  "label": "Ort",   "pflicht": True,  "fim_id": "F60000025"},
                     {"id": "datum",        "typ": "datum", "label": "Datum", "pflicht": True,  "fim_id": "F60000060"},
                     {"id": "unterschrift", "typ": "signatur", "label": "Rechtsverbindliche Unterschrift", "pflicht": True},
                     {"id": "zusammenfassung", "typ": "zusammenfassung"},
                 ]),
        ]

        schritt_map = {}
        for sd in schritte_def:
            felder = sd.pop("felder_json", [])
            obj = AntrSchritt.objects.create(pfad=pfad, felder_json=felder, **sd)
            schritt_map[obj.node_id] = obj

        transitionen_def = [
            # s01 → s02
            dict(von="s01", zu="s02", bedingung="", label="", reihenfolge=0),
            # s02 → s03
            dict(von="s02", zu="s03", bedingung="", label="", reihenfolge=0),
            # s03 → s03b (gewerblich)
            dict(von="s03", zu="s03b",
                 bedingung="{{nutzung}} == 'ausschließlich zu gewerblichen Zwecken' or {{nutzung}} == 'sowohl zu gewerblichen als auch zu Wohnzwecken'",
                 label="Gewerblich", reihenfolge=0),
            # s03 → s04 (default)
            dict(von="s03", zu="s04", bedingung="", label="", reihenfolge=1),
            # s03b → s04
            dict(von="s03b", zu="s04", bedingung="", label="", reihenfolge=0),
            # s04 → s04b (Regenwasser)
            dict(von="s04", zu="s04b",
                 bedingung="{{regen_grundwasser}} == '1'",
                 label="Regenwasser", reihenfolge=0),
            # s04 → s05 (default)
            dict(von="s04", zu="s05", bedingung="", label="", reihenfolge=1),
            # s04b → s05
            dict(von="s04b", zu="s05", bedingung="", label="", reihenfolge=0),
            # s05 → s06
            dict(von="s05", zu="s06", bedingung="", label="", reihenfolge=0),
        ]

        for td in transitionen_def:
            von = schritt_map.get(td["von"])
            zu  = schritt_map.get(td["zu"])
            if not von or not zu:
                continue
            AntrTransition.objects.create(
                pfad=pfad,
                von_schritt=von,
                zu_schritt=zu,
                bedingung=td["bedingung"],
                label=td["label"],
                reihenfolge=td["reihenfolge"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Pfad '{PFAD_NAME}' (PK {pfad.pk}) angelegt.\n"
            f"  {len(schritte_def)} Schritte | {len(transitionen_def)} Transitionen\n"
            f"  Kürzel: {pfad.kuerzel}\n"
            f"  Editor: /formulare/editor/{pfad.pk}/"
        ))
