# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: Musterpfad "Aufenthaltserlaubnis (über 18 Jahre)" importieren.

Basiert auf MACH-Formular 100002 (Stadt Bergisch Gladbach, Ausländerbehörde).
Umsetzt als dynamischer Vorgangswerk-Pfad mit 20 Schritten und bedingter Verzweigung.

Nutzung:
    python manage.py import_aufenthaltserlaubnis
    python manage.py import_aufenthaltserlaubnis --replace   # löscht vorhandenen Pfad gleichen Namens
"""
from django.core.management.base import BaseCommand
from formulare.models import AntrPfad, AntrSchritt, AntrTransition


PFAD_NAME = "Aufenthaltserlaubnis – Erteilung (über 18 Jahre)"


class Command(BaseCommand):
    help = "Importiert den Musterpfad 'Aufenthaltserlaubnis (über 18 Jahre)'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Vorhandenen Pfad gleichen Namens vorher löschen",
        )

    def handle(self, *args, **options):
        if options["replace"]:
            deleted, _ = AntrPfad.objects.filter(name=PFAD_NAME).delete()
            if deleted:
                self.stdout.write(f"  Vorhandener Pfad gelöscht.")

        pfad = AntrPfad.objects.create(
            name=PFAD_NAME,
            beschreibung=(
                "Antrag auf Erteilung einer Aufenthaltserlaubnis für Personen über 18 Jahre. "
                "Dynamischer Pfad: Ehepartner-, Kinder-, Eltern-, Studium- und Beschäftigungs-"
                "Schritte erscheinen nur wenn relevant."
            ),
            aktiv=True,
            oeffentlich=True,
            kuerzel="AUF",
            leika_schluessel="99110001000000",
        )

        # ------------------------------------------------------------------
        # Schritte definieren
        # ------------------------------------------------------------------
        schritte_def = [

            # ----------------------------------------------------------------
            # s01 – Datenschutz (START)
            # ----------------------------------------------------------------
            dict(node_id="s01", titel="Datenschutz & Einwilligung",
                 ist_start=True, ist_ende=False, pos_x=300, pos_y=80,
                 felder_json=[
                     {"id": "dsgvo", "typ": "einwilligung",
                      "text": (
                          "Ich stimme der Erhebung und Verarbeitung meiner personenbezogenen Daten "
                          "zur Bearbeitung dieses Antrags gemäß § 86 ff. AufenthG zu. "
                          "Die Daten werden ausschließlich für diesen Zweck verwendet und nach "
                          "Abschluss des Verfahrens gemäß gesetzlicher Aufbewahrungsfristen gelöscht."
                      ),
                      "pflicht": True},
                 ]),

            # ----------------------------------------------------------------
            # s02 – Antragstellende Person
            # ----------------------------------------------------------------
            dict(node_id="s02", titel="Antragstellende Person",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=230,
                 felder_json=[
                     {"id": "familienname",       "typ": "text",    "label": "Familienname",        "pflicht": True,  "fim_id": "F60000004"},
                     {"id": "geburtsname",         "typ": "text",    "label": "Geburtsname",         "pflicht": False, "fim_id": "F60000005"},
                     {"id": "vorname",             "typ": "text",    "label": "Vorname",             "pflicht": True,  "fim_id": "F60000003"},
                     {"id": "geschlecht",          "typ": "auswahl", "label": "Geschlecht",          "pflicht": False, "fim_id": "F60000010",
                      "optionen": ["weiblich", "männlich", "divers", "keine Angaben"]},
                     {"id": "geburtsdatum",        "typ": "datum",   "label": "Geburtsdatum",        "pflicht": True,  "fim_id": "F60000006"},
                     {"id": "geburtsort",          "typ": "text",    "label": "Geburtsort",          "pflicht": False, "fim_id": "F60000007"},
                     {"id": "geburtsland",         "typ": "text",    "label": "Geburtsland / Staat", "pflicht": False, "fim_id": "F60000008"},
                     {"id": "koerpergroesse",      "typ": "zahl",    "label": "Körpergröße (cm)",    "pflicht": False},
                     {"id": "augenfarbe",          "typ": "text",    "label": "Augenfarbe",          "pflicht": False},
                     {"id": "staatsangehoerigkeit","typ": "text",    "label": "Staatsangehörigkeit", "pflicht": True,  "fim_id": "F60000009"},
                     {"id": "familienstand",       "typ": "radio",   "label": "Familienstand",       "pflicht": True,
                      "optionen": ["ledig", "verheiratet", "verwitwet", "geschieden",
                                   "getrennt lebend", "in eingetragener Lebenspartnerschaft",
                                   "Lebenspartnerschaft aufgehoben"]},
                     {"id": "lp_aufgehoben_seit",  "typ": "datum",   "label": "Lebenspartnerschaft aufgehoben seit", "pflicht": False},
                     {"id": "hat_kinder",          "typ": "radio",   "label": "Haben Sie Kinder?",   "pflicht": True,
                      "optionen": ["ja", "nein"]},
                     {"id": "ist_minderjaehrig",   "typ": "radio",   "label": "Sind Sie minderjährig?", "pflicht": True,
                      "optionen": ["ja", "nein"],
                      "hilfetext": "Minderjährig = unter 18 Jahre. Relevant für Abschnitt 22 (Häusliche Gemeinschaft)."},
                 ]),

            # ----------------------------------------------------------------
            # s08 – Ehepartner / Lebenspartner (NUR wenn verheiratet/LP)
            # ----------------------------------------------------------------
            dict(node_id="s08", titel="Ehegatte / Lebenspartner",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=230,
                 felder_json=[
                     {"id": "abschnitt_ehe",          "typ": "abschnitt", "text": "Angaben zum Ehegatten / zur Lebenspartnerin"},
                     {"id": "ehe_familienname",        "typ": "text",    "label": "Familienname",        "pflicht": True,  "fim_id": "F60000004"},
                     {"id": "ehe_geburtsname",         "typ": "text",    "label": "Geburtsname",         "pflicht": False, "fim_id": "F60000005"},
                     {"id": "ehe_vorname",             "typ": "text",    "label": "Vorname",             "pflicht": True,  "fim_id": "F60000003"},
                     {"id": "ehe_geburtsdatum",        "typ": "datum",   "label": "Geburtsdatum",        "pflicht": False, "fim_id": "F60000006"},
                     {"id": "ehe_geburtsort",          "typ": "text",    "label": "Geburtsort",          "pflicht": False, "fim_id": "F60000007"},
                     {"id": "ehe_geburtsland",         "typ": "text",    "label": "Geburtsland / Staat", "pflicht": False},
                     {"id": "abschnitt_ehe_brd",       "typ": "abschnitt", "text": "Anschrift in der BRD"},
                     {"id": "ehe_strasse",             "typ": "text",    "label": "Straße / Postfach",   "pflicht": False, "fim_id": "F60000020"},
                     {"id": "ehe_hausnummer",          "typ": "text",    "label": "Hausnummer",          "pflicht": False, "fim_id": "F60000021"},
                     {"id": "ehe_plz",                 "typ": "plz",     "label": "Postleitzahl",        "pflicht": False, "fim_id": "F60000024"},
                     {"id": "ehe_ort",                 "typ": "text",    "label": "Ort",                 "pflicht": False, "fim_id": "F60000025"},
                     {"id": "abschnitt_ehe_ausland",   "typ": "abschnitt", "text": "Anschrift im Ausland (falls abweichend)"},
                     {"id": "ehe_ausland_adresse",     "typ": "text",    "label": "Adressangaben",       "pflicht": False},
                     {"id": "ehe_ausland_ort",         "typ": "text",    "label": "Ort",                 "pflicht": False},
                     {"id": "ehe_ausland_staat",       "typ": "text",    "label": "Staat",               "pflicht": False},
                     {"id": "ehe_telefon",             "typ": "telefon", "label": "Telefon",             "pflicht": False, "fim_id": "F60000031"},
                     {"id": "ehe_email",               "typ": "email",   "label": "E-Mail",              "pflicht": False, "fim_id": "F60000030"},
                     {"id": "ehe_status",              "typ": "radio",   "label": "Ausländerrechtlicher Status", "pflicht": False,
                      "optionen": ["Niederlassungserlaubnis", "Aufenthaltserlaubnis", "Visum", "Asylberechtigt"]},
                 ]),

            # ----------------------------------------------------------------
            # s09 – Kinder (NUR wenn hat_kinder == ja)
            # ----------------------------------------------------------------
            dict(node_id="s09", titel="Kinder",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=430,
                 felder_json=[
                     {"id": "kinder", "typ": "gruppe", "label": "Kinder",
                      "singular": "Kind", "pflicht": False,
                      "unterfelder": [
                          {"id": "kind_familienname", "typ": "text",    "label": "Familienname",        "pflicht": True},
                          {"id": "kind_vorname",      "typ": "text",    "label": "Vorname",             "pflicht": True},
                          {"id": "kind_geschlecht",   "typ": "auswahl", "label": "Geschlecht",
                           "optionen": ["weiblich", "männlich", "divers", "keine Angaben"]},
                          {"id": "kind_geburtsdatum", "typ": "datum",   "label": "Geburtsdatum"},
                          {"id": "kind_geburtsort",   "typ": "text",    "label": "Geburtsort"},
                          {"id": "kind_geburtsland",  "typ": "text",    "label": "Geburtsland / Staat"},
                          {"id": "kind_strasse",      "typ": "text",    "label": "Straße"},
                          {"id": "kind_hausnummer",   "typ": "text",    "label": "Hausnummer"},
                          {"id": "kind_plz",          "typ": "text",    "label": "PLZ"},
                          {"id": "kind_ort",          "typ": "text",    "label": "Ort"},
                          {"id": "kind_mitreisend",   "typ": "auswahl", "label": "Reist das Kind mit ein?",
                           "optionen": ["ja", "nein"]},
                      ]},
                 ]),

            # ----------------------------------------------------------------
            # s03 – Aufenthaltsort
            # ----------------------------------------------------------------
            dict(node_id="s03", titel="Aufenthaltsort in Deutschland",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=430,
                 felder_json=[
                     {"id": "bezugsperson_name",  "typ": "text",    "label": "Name Arbeitgeber / Verwandter / Ausbildungsstätte / Bezugsperson", "pflicht": False},
                     {"id": "aufenthalt_strasse",  "typ": "text",    "label": "Straße / Postfach",  "pflicht": True,  "fim_id": "F60000020"},
                     {"id": "aufenthalt_hnr",      "typ": "text",    "label": "Hausnummer",         "pflicht": False, "fim_id": "F60000021"},
                     {"id": "aufenthalt_plz",      "typ": "plz",     "label": "Postleitzahl",       "pflicht": True,  "fim_id": "F60000024"},
                     {"id": "aufenthalt_ort",      "typ": "text",    "label": "Ort",                "pflicht": True,  "fim_id": "F60000025"},
                     {"id": "aufenthalt_telefon",  "typ": "telefon", "label": "Telefon",            "pflicht": False, "fim_id": "F60000031"},
                     {"id": "aufenthalt_fax",      "typ": "telefon", "label": "Fax",                "pflicht": False},
                     {"id": "aufenthalt_email",    "typ": "email",   "label": "E-Mail",             "pflicht": False, "fim_id": "F60000030"},
                     {"id": "unterkunft_art",      "typ": "radio",   "label": "Form der Unterbringung", "pflicht": True,
                      "optionen": ["Hotel", "Zimmer", "Sammelunterkunft", "Wohnung"]},
                     {"id": "wohnflaeche",         "typ": "zahl",    "label": "Wohnfläche (m²) – nur bei Wohnung", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s04 – Aufenthaltsgrund
            # ----------------------------------------------------------------
            dict(node_id="s04", titel="Grund / Berechtigung des Aufenthalts",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=580,
                 felder_json=[
                     {"id": "aufenthaltsgrund_ausbildung",      "typ": "bool", "label": "Ausbildung (§§ 16–17 AufenthG)"},
                     {"id": "aufenthaltsgrund_erwerbstaetigkeit","typ": "bool", "label": "Erwerbstätigkeit (§§ 18–21 AufenthG)"},
                     {"id": "aufenthaltsgrund_humanitaer",      "typ": "bool", "label": "Völkerrechtliche, humanitäre oder politische Gründe (§§ 22–26, 104a AufenthG)"},
                     {"id": "aufenthaltsgrund_familie",         "typ": "bool", "label": "Familiäre Gründe (§§ 27–36a AufenthG)"},
                     {"id": "aufenthaltsgrund_besondere",       "typ": "bool", "label": "Besondere Aufenthaltsrechte (§§ 37–38a AufenthG)"},
                     {"id": "aufenthaltsgrund_sonstige",        "typ": "mehrzeil", "label": "Sonstige Angaben (optional)", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s07 – Eltern (NUR bei familiären Gründen)
            # ----------------------------------------------------------------
            dict(node_id="s07", titel="Familie – Elternteile",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=580,
                 felder_json=[
                     {"id": "abschnitt_vater",   "typ": "abschnitt", "text": "Elternteil 1 – Vater"},
                     {"id": "vater_familienname","typ": "text",    "label": "Familienname",        "pflicht": False, "fim_id": "F60000004"},
                     {"id": "vater_geburtsname", "typ": "text",    "label": "Geburtsname",         "pflicht": False, "fim_id": "F60000005"},
                     {"id": "vater_vorname",     "typ": "text",    "label": "Vorname",             "pflicht": False, "fim_id": "F60000003"},
                     {"id": "vater_geburtsdatum","typ": "datum",   "label": "Geburtsdatum",        "pflicht": False, "fim_id": "F60000006"},
                     {"id": "vater_geburtsort",  "typ": "text",    "label": "Geburtsort",          "pflicht": False},
                     {"id": "vater_geburtsland", "typ": "text",    "label": "Geburtsland / Staat", "pflicht": False},
                     {"id": "vater_strasse",     "typ": "text",    "label": "Straße",              "pflicht": False},
                     {"id": "vater_plz",         "typ": "plz",     "label": "PLZ",                 "pflicht": False},
                     {"id": "vater_ort",         "typ": "text",    "label": "Ort",                 "pflicht": False},
                     {"id": "vater_status",      "typ": "radio",   "label": "Ausländerrechtlicher Status", "pflicht": False,
                      "optionen": ["Niederlassungserlaubnis", "Aufenthaltserlaubnis"]},
                     {"id": "vater_aufenthalt_bis", "typ": "datum","label": "Aufenthaltserlaubnis befristet bis", "pflicht": False},
                     {"id": "vater_telefon",     "typ": "telefon", "label": "Telefon",             "pflicht": False},
                     {"id": "vater_email",       "typ": "email",   "label": "E-Mail",              "pflicht": False},
                     {"id": "abschnitt_mutter",  "typ": "abschnitt", "text": "Elternteil 2 – Mutter"},
                     {"id": "mutter_familienname","typ": "text",   "label": "Familienname",        "pflicht": False, "fim_id": "F60000004"},
                     {"id": "mutter_geburtsname","typ": "text",    "label": "Geburtsname",         "pflicht": False, "fim_id": "F60000005"},
                     {"id": "mutter_vorname",    "typ": "text",    "label": "Vorname",             "pflicht": False, "fim_id": "F60000003"},
                     {"id": "mutter_geburtsdatum","typ": "datum",  "label": "Geburtsdatum",        "pflicht": False},
                     {"id": "mutter_geburtsort", "typ": "text",    "label": "Geburtsort",          "pflicht": False},
                     {"id": "mutter_geburtsland","typ": "text",    "label": "Geburtsland / Staat", "pflicht": False},
                     {"id": "mutter_strasse",    "typ": "text",    "label": "Straße",              "pflicht": False},
                     {"id": "mutter_plz",        "typ": "plz",     "label": "PLZ",                 "pflicht": False},
                     {"id": "mutter_ort",        "typ": "text",    "label": "Ort",                 "pflicht": False},
                     {"id": "mutter_status",     "typ": "radio",   "label": "Ausländerrechtlicher Status", "pflicht": False,
                      "optionen": ["Niederlassungserlaubnis", "Aufenthaltserlaubnis"]},
                     {"id": "mutter_aufenthalt_bis","typ": "datum","label": "Aufenthaltserlaubnis befristet bis", "pflicht": False},
                     {"id": "mutter_telefon",    "typ": "telefon", "label": "Telefon",             "pflicht": False},
                     {"id": "mutter_email",      "typ": "email",   "label": "E-Mail",              "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s05 – Ausweis / Pass
            # ----------------------------------------------------------------
            dict(node_id="s05", titel="Ausweis / Reisepass",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=730,
                 felder_json=[
                     {"id": "ausweis_art",         "typ": "text",  "label": "Art des Ausweisdokumentes", "pflicht": True},
                     {"id": "ausweis_passnummer",  "typ": "text",  "label": "Passnummer",          "pflicht": True,  "fim_id": "F60000041"},
                     {"id": "ausweis_ausstellung", "typ": "datum", "label": "Ausstellungsdatum",   "pflicht": False},
                     {"id": "ausweis_gueltigkeit", "typ": "datum", "label": "Gültig bis",          "pflicht": True},
                     {"id": "ausweis_behoerde",    "typ": "text",  "label": "Ausstellungsbehörde", "pflicht": False},
                     {"id": "ausweis_strasse",     "typ": "text",  "label": "Straße / Postfach",   "pflicht": False},
                     {"id": "ausweis_plz",         "typ": "plz",   "label": "PLZ",                 "pflicht": False},
                     {"id": "ausweis_ort",         "typ": "text",  "label": "Ort",                 "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s06 – Einreise
            # ----------------------------------------------------------------
            dict(node_id="s06", titel="Einreise in die Bundesrepublik",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=880,
                 felder_json=[
                     {"id": "einreise_seit_geburt","typ": "bool",   "label": "Ich halte mich seit Geburt in Deutschland auf"},
                     {"id": "einreise_datum",      "typ": "datum",  "label": "Aufenthalt seit (Datum)", "pflicht": False,
                      "hilfetext": "Nur ausfüllen wenn nicht seit Geburt"},
                     {"id": "einreise_mit_visum",  "typ": "radio",  "label": "Erfolgte die Einreise mit einem Visum?", "pflicht": True,
                      "optionen": ["ja", "nein"]},
                     {"id": "einreise_zweck",      "typ": "mehrzeil","label": "Zweck / Grund der Einreise", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s06b – Visum-Details (NUR wenn Einreise mit Visum)
            # ----------------------------------------------------------------
            dict(node_id="s06b", titel="Visum – Details",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=880,
                 felder_json=[
                     {"id": "visum_botschaft",       "typ": "text",  "label": "Name der deutschen Botschaft / Konsulat", "pflicht": True},
                     {"id": "visum_land",             "typ": "text",  "label": "Land",                "pflicht": True},
                     {"id": "visum_strasse",          "typ": "text",  "label": "Straße",              "pflicht": False},
                     {"id": "visum_plz",              "typ": "plz",   "label": "PLZ",                 "pflicht": False},
                     {"id": "visum_ort",              "typ": "text",  "label": "Ort",                 "pflicht": False},
                     {"id": "visum_beginn",           "typ": "datum", "label": "Gültig ab",           "pflicht": False},
                     {"id": "visum_ende",             "typ": "datum", "label": "Gültig bis",          "pflicht": True},
                     {"id": "visum_zustimmung_ab",    "typ": "radio", "label": "Wurde das Visum mit Zustimmung der Ausländerbehörde erteilt?",
                      "pflicht": False, "optionen": ["ja", "nein"]},
                 ]),

            # ----------------------------------------------------------------
            # s10 – Aufenthaltsdauer & Mitreisende
            # ----------------------------------------------------------------
            dict(node_id="s10", titel="Aufenthaltsdauer & Mitreisende",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1030,
                 felder_json=[
                     {"id": "abschnitt_dauer",       "typ": "abschnitt", "text": "Geplante Aufenthaltsdauer"},
                     {"id": "aufenthalt_einreise",   "typ": "datum",  "label": "Geplante Einreise",  "pflicht": False},
                     {"id": "aufenthalt_ausreise",   "typ": "datum",  "label": "Geplante Ausreise",  "pflicht": False},
                     {"id": "abschnitt_mitreise",    "typ": "abschnitt", "text": "Mitreisende Familienangehörige"},
                     {"id": "mitreise_ehepartner",   "typ": "bool",   "label": "Ehegatte / Lebenspartner reist mit"},
                     {"id": "mitreise_kinder",       "typ": "bool",   "label": "Kinder reisen mit (siehe Angaben unter Kinder)"},
                     {"id": "mitreise_sonstige",     "typ": "mehrzeil","label": "Sonstige mitreisende Personen", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s11 – Anschrift im Ausland
            # ----------------------------------------------------------------
            dict(node_id="s11", titel="Anschrift im Ausland",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1180,
                 felder_json=[
                     {"id": "ausland_strasse",       "typ": "text",   "label": "Straße",             "pflicht": False},
                     {"id": "ausland_plz",           "typ": "text",   "label": "PLZ",                "pflicht": False},
                     {"id": "ausland_ort",           "typ": "text",   "label": "Ort",                "pflicht": False},
                     {"id": "ausland_zusatz",        "typ": "text",   "label": "Adresszusatz",       "pflicht": False},
                     {"id": "ausland_land",          "typ": "text",   "label": "Land",               "pflicht": False},
                     {"id": "ausland_telefon",       "typ": "telefon","label": "Telefon",            "pflicht": False},
                     {"id": "ausland_email",         "typ": "email",  "label": "E-Mail",             "pflicht": False},
                     {"id": "ausland_beibehalten",   "typ": "radio",  "label": "Auslandsadresse wird beibehalten",
                      "optionen": ["ja", "nein"], "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s12 – Lebensunterhalt
            # ----------------------------------------------------------------
            dict(node_id="s12", titel="Bestreitung des Lebensunterhaltes",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1330,
                 felder_json=[
                     {"id": "sozialleistungen",   "typ": "radio",   "label": "Erhalten Sie oder eine unterhaltspflichtige Person Sozialleistungen / Hilfe zur Erziehung?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "einkommen",          "typ": "gruppe",  "label": "Einkommensquellen",
                      "singular": "Einkommensart", "pflicht": False,
                      "unterfelder": [
                          {"id": "einkommensart",  "typ": "text", "label": "Einkommensart (z.B. Arbeitslohn, Rente, Unterhalt)"},
                          {"id": "betrag_monat",   "typ": "zahl", "label": "Betrag pro Monat (€)"},
                      ]},
                 ]),

            # ----------------------------------------------------------------
            # s13 – Krankenversicherung
            # ----------------------------------------------------------------
            dict(node_id="s13", titel="Krankenversicherungsschutz",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1480,
                 felder_json=[
                     {"id": "krankenversicherung", "typ": "mehrzeil", "label": "Art, Umfang, Versicherungsunternehmen",
                      "pflicht": True,
                      "hilfetext": "z.B. 'Gesetzlich versichert bei AOK, Vollschutz' oder 'Private Krankenversicherung, XY Versicherung AG'"},
                 ]),

            # ----------------------------------------------------------------
            # s14 – Integrationskurs
            # ----------------------------------------------------------------
            dict(node_id="s14", titel="Integrationskurs",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1630,
                 felder_json=[
                     {"id": "integrationskurs",     "typ": "radio",   "label": "Haben Sie an einem Integrationskurs (§ 43 AufenthG) teilgenommen?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "integrationskurs_art", "typ": "radio",   "label": "Art des Kurses",
                      "pflicht": False, "optionen": ["Basiskurs", "Basis- und Aufbaukurs"],
                      "hilfetext": "Nur ausfüllen wenn ja. Bitte Bescheinigung über den Abschlusstest beifügen."},
                 ]),

            # ----------------------------------------------------------------
            # s15 – Bisherige Aufenthalte in Deutschland
            # ----------------------------------------------------------------
            dict(node_id="s15", titel="Bisherige Aufenthalte in Deutschland",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1780,
                 felder_json=[
                     {"id": "fruehereaufenthalte",  "typ": "gruppe",  "label": "Bisherige Aufenthalte",
                      "singular": "Aufenthalt", "pflicht": False,
                      "hilfetext": "Nur ausfüllen sofern zutreffend",
                      "unterfelder": [
                          {"id": "aufenthaltsort", "typ": "text",  "label": "Aufenthaltsort"},
                          {"id": "aufenthalt_von", "typ": "datum", "label": "Von"},
                          {"id": "aufenthalt_bis", "typ": "datum", "label": "Bis"},
                      ]},
                 ]),

            # ----------------------------------------------------------------
            # s16 – Aufenthaltstitel & Asylantrag
            # ----------------------------------------------------------------
            dict(node_id="s16", titel="Aufenthaltstitel & Asylantrag",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=1930,
                 felder_json=[
                     {"id": "abschnitt_niederlassung",    "typ": "abschnitt", "text": "Niederlassungserlaubnis"},
                     {"id": "niederlassung_beantragt",    "typ": "radio",   "label": "Haben Sie einen Antrag auf Erteilung einer Niederlassungserlaubnis gestellt?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "niederlassung_datum",        "typ": "datum",   "label": "Datum des Antrags",        "pflicht": False},
                     {"id": "niederlassung_aktenzeichen", "typ": "text",    "label": "Aktenzeichen",             "pflicht": False},
                     {"id": "niederlassung_behoerde",     "typ": "text",    "label": "Name der Behörde",         "pflicht": False},
                     {"id": "niederlassung_entscheidung", "typ": "mehrzeil","label": "Entscheidung",             "pflicht": False},
                     {"id": "abschnitt_asyl",             "typ": "abschnitt", "text": "Asylantrag"},
                     {"id": "asylantrag_gestellt",        "typ": "radio",   "label": "Haben Sie einen Asylantrag gestellt?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "asylantrag_datum",           "typ": "datum",   "label": "Datum",                    "pflicht": False},
                     {"id": "asylantrag_aktenzeichen",    "typ": "text",    "label": "Aktenzeichen",             "pflicht": False},
                     {"id": "asylantrag_behoerde",        "typ": "text",    "label": "Name der Behörde",         "pflicht": False},
                     {"id": "asylantrag_entscheidung",    "typ": "mehrzeil","label": "Entscheidung",             "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s17 – Einreiseverweigerung & Straftaten
            # ----------------------------------------------------------------
            dict(node_id="s17", titel="Einreiseverweigerung & Rechtsverstöße",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=2080,
                 felder_json=[
                     {"id": "abschnitt_einreise_verw", "typ": "abschnitt", "text": "Einreiseverweigerung / Ausweisung / Abschiebung"},
                     {"id": "einreise_verweigert",     "typ": "radio",   "label": "Wurde Ihnen schon einmal die Einreise in die BRD oder einen Schengen-Staat verweigert?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "einreise_verw_eintraege", "typ": "gruppe",  "label": "Einreiseverweigerungen",
                      "singular": "Eintrag", "pflicht": False,
                      "unterfelder": [
                          {"id": "verw_datum",       "typ": "datum", "label": "Datum"},
                          {"id": "verw_aktenzeichen","typ": "text",  "label": "Aktenzeichen"},
                          {"id": "verw_behoerde",    "typ": "text",  "label": "Name der Behörde"},
                          {"id": "verw_strasse",     "typ": "text",  "label": "Straße"},
                          {"id": "verw_plz",         "typ": "text",  "label": "PLZ"},
                          {"id": "verw_ort",         "typ": "text",  "label": "Ort"},
                      ]},
                     {"id": "abschnitt_straftaten",   "typ": "abschnitt", "text": "Rechtsverstöße / Straftaten"},
                     {"id": "rechtsverstoesse",        "typ": "radio",   "label": "Haben Sie in der Vergangenheit Rechtsverstöße begangen?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "vorbestraft",             "typ": "radio",   "label": "Sind Sie vorbestraft?",
                      "pflicht": False, "optionen": ["ja", "nein"]},
                     {"id": "vorstrafe_datum",         "typ": "datum",   "label": "Datum der Verurteilung",  "pflicht": False},
                     {"id": "vorstrafe_grund",         "typ": "text",    "label": "Grund",                   "pflicht": False},
                     {"id": "vorstrafe_strafe",        "typ": "mehrzeil","label": "Strafe",                  "pflicht": False},
                     {"id": "rechtsverstoess_wo",      "typ": "radio",   "label": "Wo wurde der Rechtsverstoß begangen?",
                      "pflicht": False, "optionen": ["in Deutschland", "im Ausland"]},
                     {"id": "ermittlungen_laufend",    "typ": "radio",   "label": "Wird gegen Sie aufgrund des Verdachts einer Straftat ermittelt?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "ermittlungen_behoerde",   "typ": "text",    "label": "Durchführende Behörde (nur wenn ja)", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s18 – Politische Betätigung
            # ----------------------------------------------------------------
            dict(node_id="s18", titel="Politische Betätigung",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=2230,
                 felder_json=[
                     {"id": "politik_brd_geplant",     "typ": "radio",   "label": "Beabsichtigen Sie sich in der BRD politisch zu betätigen?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "politik_brd_umfang",      "typ": "mehrzeil","label": "Art und Umfang (nur wenn ja)", "pflicht": False},
                     {"id": "politik_heimatland",      "typ": "radio",   "label": "Haben Sie sich in Ihrem Heimatland politisch betätigt?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "politik_heimatland_umfang","typ": "mehrzeil","label": "Art und Umfang (nur wenn ja)", "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s19 – Schulbesuche
            # ----------------------------------------------------------------
            dict(node_id="s19", titel="Schulbesuche in Deutschland",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=2380,
                 felder_json=[
                     {"id": "schulbesuche", "typ": "gruppe", "label": "Schulbesuche in Deutschland",
                      "singular": "Schulbesuch", "pflicht": False,
                      "hilfetext": "Nur ausfüllen sofern zutreffend",
                      "unterfelder": [
                          {"id": "schule_name",  "typ": "text",  "label": "Schule"},
                          {"id": "schule_von",   "typ": "datum", "label": "Von"},
                          {"id": "schule_bis",   "typ": "datum", "label": "Bis"},
                          {"id": "schule_abschluss", "typ": "text", "label": "Abschluss"},
                      ]},
                 ]),

            # ----------------------------------------------------------------
            # s20 – Häusliche Gemeinschaft (NUR Minderjährige)
            # ----------------------------------------------------------------
            dict(node_id="s20", titel="Häusliche Gemeinschaft (Minderjährige)",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=2380,
                 felder_json=[
                     {"id": "hg_elternteil1",        "typ": "bool",  "label": "Häusliche Gemeinschaft mit Elternteil 1"},
                     {"id": "hg_elternteil2",        "typ": "bool",  "label": "Häusliche Gemeinschaft mit Elternteil 2"},
                     {"id": "hg_sonstige",           "typ": "text",  "label": "Sonstige Personen", "pflicht": False},
                     {"id": "hg_aufenthalt_et1",     "typ": "bool",  "label": "Aufenthalts-/Niederlassungserlaubnis liegt vor für Elternteil 1"},
                     {"id": "hg_aufenthalt_et2",     "typ": "bool",  "label": "Aufenthalts-/Niederlassungserlaubnis liegt vor für Elternteil 2"},
                     {"id": "hg_asyl_anerkannt",     "typ": "radio", "label": "Ist eine der folgenden Personen unanfechtbar asylberechtigt anerkannt?",
                      "pflicht": False, "optionen": ["nein", "Elternteil 1", "Elternteil 2"]},
                 ]),

            # ----------------------------------------------------------------
            # s21 – Studium (NUR bei Ausbildungsaufenthalt)
            # ----------------------------------------------------------------
            dict(node_id="s21", titel="Zusatzangaben: Studium",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=2530,
                 felder_json=[
                     {"id": "studium_aufgenommen",  "typ": "radio",  "label": "Haben Sie Ihre Studientätigkeit bereits aufgenommen?",
                      "pflicht": True, "optionen": ["ja", "nein"]},
                     {"id": "studium_hochschule",   "typ": "text",   "label": "Name der Hochschule",  "pflicht": False},
                     {"id": "studium_fachrichtung", "typ": "text",   "label": "Fachrichtung",         "pflicht": False},
                     {"id": "studium_strasse",      "typ": "text",   "label": "Straße",               "pflicht": False},
                     {"id": "studium_plz",          "typ": "plz",    "label": "PLZ",                  "pflicht": False},
                     {"id": "studium_ort",          "typ": "text",   "label": "Ort",                  "pflicht": False},
                 ]),

            # ----------------------------------------------------------------
            # s22 – Beschäftigung (NUR bei Erwerbstätigkeit)
            # ----------------------------------------------------------------
            dict(node_id="s22", titel="Zusatzangaben: Beschäftigung",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=2680,
                 felder_json=[
                     {"id": "abschnitt_unselbst",      "typ": "abschnitt", "text": "24.1 Unselbständige Tätigkeit"},
                     {"id": "arbeitgeber_name",        "typ": "text",    "label": "Name des Arbeitgebers",       "pflicht": False},
                     {"id": "arbeitgeber_strasse",     "typ": "text",    "label": "Straße",                      "pflicht": False},
                     {"id": "arbeitgeber_plz",         "typ": "plz",     "label": "PLZ",                         "pflicht": False},
                     {"id": "arbeitgeber_ort",         "typ": "text",    "label": "Ort",                         "pflicht": False},
                     {"id": "arbeitgeber_telefon",     "typ": "telefon", "label": "Telefon",                     "pflicht": False},
                     {"id": "arbeitgeber_email",       "typ": "email",   "label": "E-Mail",                      "pflicht": False},
                     {"id": "bundesagentur_zustimmung","typ": "bool",    "label": "Zustimmung der Bundesagentur für Arbeit liegt vor (bitte in Kopie beifügen)"},
                     {"id": "abschnitt_selbst",        "typ": "abschnitt", "text": "24.2 Selbständige Tätigkeit"},
                     {"id": "firma_name",              "typ": "text",    "label": "Firma",                       "pflicht": False},
                     {"id": "firma_branche",           "typ": "text",    "label": "Tätigkeitsfeld / Branche",    "pflicht": False},
                     {"id": "firma_strasse",           "typ": "text",    "label": "Straße",                      "pflicht": False},
                     {"id": "firma_plz",               "typ": "plz",     "label": "PLZ",                         "pflicht": False},
                     {"id": "firma_ort",               "typ": "text",    "label": "Ort",                         "pflicht": False},
                     {"id": "finanzierung_gesichert",  "typ": "bool",    "label": "Finanzierung durch Fremd-/Eigenkapital gesichert (bitte belegen)"},
                 ]),

            # ----------------------------------------------------------------
            # s23 – Ergänzungen & Anlagen
            # ----------------------------------------------------------------
            dict(node_id="s23", titel="Ergänzungen & Anlagen",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=2830,
                 felder_json=[
                     {"id": "ergaenzungen", "typ": "mehrzeil", "label": "Ergänzende Angaben",    "pflicht": False},
                     {"id": "anlagen",      "typ": "mehrzeil", "label": "Beizufügende Anlagen",  "pflicht": False,
                      "hilfetext": "Bitte listen Sie alle beigefügten Unterlagen auf"},
                 ]),

            # ----------------------------------------------------------------
            # s24 – Unterschrift (ENDE)
            # ----------------------------------------------------------------
            dict(node_id="s24", titel="Erklärung & Unterschrift",
                 ist_start=False, ist_ende=True, pos_x=300, pos_y=2980,
                 felder_json=[
                     {"id": "hinweis_strafbarkeit", "typ": "textblock",
                      "text": (
                          "Ich wurde darauf hingewiesen, dass ich gemäß § 82 Abs. 1 AufenthG verpflichtet bin, "
                          "die für die Entscheidung notwendigen Auskünfte zu geben, dass ich mich bei unrichtiger "
                          "oder unvollständiger Angabe nach § 95 Abs. 2 AufenthG strafbar mache und dadurch ein "
                          "Ausweisungstatbestand nach §§ 53 ff. AufenthG erfüllt ist."
                      )},
                     {"id": "bestaetigung",        "typ": "einwilligung",
                      "text": (
                          "Ich versichere, vorstehende Angaben nach bestem Wissen und Gewissen richtig und vollständig "
                          "gemacht zu haben. Mir ist bekannt, dass falsche oder unzutreffende Angaben ein Grund für den "
                          "Entzug der Aufenthaltserlaubnis sind."
                      ),
                      "pflicht": True},
                     {"id": "unterschrift_ort",    "typ": "text",     "label": "Ort",       "pflicht": True,  "fim_id": "F60000025"},
                     {"id": "unterschrift_datum",  "typ": "datum",    "label": "Datum",     "pflicht": True,  "fim_id": "F60000060"},
                     {"id": "zusammenfassung",     "typ": "zusammenfassung"},
                 ]),
        ]

        # Schritte anlegen
        schritt_map = {}
        for sd in schritte_def:
            felder = sd.pop("felder_json", [])
            obj = AntrSchritt.objects.create(pfad=pfad, felder_json=felder, **sd)
            schritt_map[obj.node_id] = obj

        # ------------------------------------------------------------------
        # Transitionen
        # Reihenfolge bestimmt Priorität: niedrigste zuerst geprüft
        # ------------------------------------------------------------------
        transitionen_def = [
            # s01 → s02 (immer)
            dict(von="s01", zu="s02", bedingung="", label="", reihenfolge=0),

            # s02 → s08 (wenn verheiratet oder LP)
            dict(von="s02", zu="s08",
                 bedingung="{{familienstand}} == 'verheiratet' or {{familienstand}} == 'in eingetragener Lebenspartnerschaft'",
                 label="Verheiratet / LP", reihenfolge=0),
            # s02 → s09 (wenn Kinder, aber ledig/verwitwet/etc.)
            dict(von="s02", zu="s09",
                 bedingung="{{hat_kinder}} == 'ja'",
                 label="Kinder vorhanden", reihenfolge=1),
            # s02 → s03 (default)
            dict(von="s02", zu="s03", bedingung="", label="", reihenfolge=2),

            # s08 → s09 (wenn Kinder vorhanden)
            dict(von="s08", zu="s09",
                 bedingung="{{hat_kinder}} == 'ja'",
                 label="Kinder vorhanden", reihenfolge=0),
            # s08 → s03 (default)
            dict(von="s08", zu="s03", bedingung="", label="", reihenfolge=1),

            # s09 → s03 (immer)
            dict(von="s09", zu="s03", bedingung="", label="", reihenfolge=0),

            # s03 → s04 (immer)
            dict(von="s03", zu="s04", bedingung="", label="", reihenfolge=0),

            # s04 → s07 (wenn familiäre Gründe)
            dict(von="s04", zu="s07",
                 bedingung="{{aufenthaltsgrund_familie}} == '1'",
                 label="Familiäre Gründe", reihenfolge=0),
            # s04 → s05 (default)
            dict(von="s04", zu="s05", bedingung="", label="", reihenfolge=1),

            # s07 → s05 (immer)
            dict(von="s07", zu="s05", bedingung="", label="", reihenfolge=0),

            # s05 → s06 (immer)
            dict(von="s05", zu="s06", bedingung="", label="", reihenfolge=0),

            # s06 → s06b (wenn Visum)
            dict(von="s06", zu="s06b",
                 bedingung="{{einreise_mit_visum}} == 'ja'",
                 label="Mit Visum", reihenfolge=0),
            # s06 → s10 (default)
            dict(von="s06", zu="s10", bedingung="", label="", reihenfolge=1),

            # s06b → s10 (immer)
            dict(von="s06b", zu="s10", bedingung="", label="", reihenfolge=0),

            # s10 → s11 (immer)
            dict(von="s10", zu="s11", bedingung="", label="", reihenfolge=0),

            # s11 → s12 (immer)
            dict(von="s11", zu="s12", bedingung="", label="", reihenfolge=0),

            # s12 → s13 (immer)
            dict(von="s12", zu="s13", bedingung="", label="", reihenfolge=0),

            # s13 → s14 (immer)
            dict(von="s13", zu="s14", bedingung="", label="", reihenfolge=0),

            # s14 → s15 (immer)
            dict(von="s14", zu="s15", bedingung="", label="", reihenfolge=0),

            # s15 → s16 (immer)
            dict(von="s15", zu="s16", bedingung="", label="", reihenfolge=0),

            # s16 → s17 (immer)
            dict(von="s16", zu="s17", bedingung="", label="", reihenfolge=0),

            # s17 → s18 (immer)
            dict(von="s17", zu="s18", bedingung="", label="", reihenfolge=0),

            # s18 → s20 (wenn minderjährig)
            dict(von="s18", zu="s20",
                 bedingung="{{ist_minderjaehrig}} == 'ja'",
                 label="Minderjährig", reihenfolge=0),
            # s18 → s19 (default)
            dict(von="s18", zu="s19", bedingung="", label="", reihenfolge=1),

            # s20 → s19 (immer)
            dict(von="s20", zu="s19", bedingung="", label="", reihenfolge=0),

            # s19 → s21 (wenn Ausbildung)
            dict(von="s19", zu="s21",
                 bedingung="{{aufenthaltsgrund_ausbildung}} == '1'",
                 label="Studium", reihenfolge=0),
            # s19 → s22 (wenn Erwerbstätigkeit, aber kein Studium)
            dict(von="s19", zu="s22",
                 bedingung="{{aufenthaltsgrund_erwerbstaetigkeit}} == '1'",
                 label="Erwerbstätigkeit", reihenfolge=1),
            # s19 → s23 (default)
            dict(von="s19", zu="s23", bedingung="", label="", reihenfolge=2),

            # s21 → s22 (wenn auch Erwerbstätigkeit)
            dict(von="s21", zu="s22",
                 bedingung="{{aufenthaltsgrund_erwerbstaetigkeit}} == '1'",
                 label="Auch Erwerbstätigkeit", reihenfolge=0),
            # s21 → s23 (default)
            dict(von="s21", zu="s23", bedingung="", label="", reihenfolge=1),

            # s22 → s23 (immer)
            dict(von="s22", zu="s23", bedingung="", label="", reihenfolge=0),

            # s23 → s24 (immer)
            dict(von="s23", zu="s24", bedingung="", label="", reihenfolge=0),
        ]

        for td in transitionen_def:
            von = schritt_map.get(td["von"])
            zu  = schritt_map.get(td["zu"])
            if not von or not zu:
                self.stderr.write(f"  Warnung: Transition {td['von']}→{td['zu']} nicht gefunden")
                continue
            AntrTransition.objects.create(
                pfad=pfad,
                von_schritt=von,
                zu_schritt=zu,
                bedingung=td["bedingung"],
                label=td["label"],
                reihenfolge=td["reihenfolge"],
            )

        schritte_anzahl    = len(schritte_def)
        transitionen_anzahl = len(transitionen_def)
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Pfad '{PFAD_NAME}' (PK {pfad.pk}) angelegt.\n"
            f"  {schritte_anzahl} Schritte | {transitionen_anzahl} Transitionen\n"
            f"  LeiKa: {pfad.leika_schluessel} | Kürzel: {pfad.kuerzel}\n"
            f"  Editor: /formulare/editor/{pfad.pk}/"
        ))
