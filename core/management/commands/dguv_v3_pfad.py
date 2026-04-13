# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: DGUV Vorschrift 3 Prüfprotokoll anlegen.

Erstellt einen vollständigen Prüfprotokoll-Pfad für die Prüfung
ortsveränderlicher elektrischer Betriebsmittel nach DGUV V3 / VDE 0701-0702.

Geeignet für Elektrofachkräfte (EFK) und elektrotechnisch unterwiesene
Personen (EuP) – mit Verzweigung je nach Qualifikation.

Nutzung:
    python manage.py dguv_v3_pfad
    python manage.py dguv_v3_pfad --reset
"""
from django.core.management.base import BaseCommand

from formulare.models import AntrPfad, AntrSchritt, AntrTransition
from workflow.models import WorkflowStep, WorkflowTemplate, WorkflowTransition

PFAD_NAME    = "DGUV V3 – Prüfprotokoll ortsveränderliche Betriebsmittel"
WORKFLOW_NAME = "DGUV V3 – Mängelbearbeitung"
PFAD_KUERZEL = "DGUV3"


class Command(BaseCommand):
    help = "Legt DGUV-V3-Prüfprotokoll-Pfad + Mängelbearbeitungs-Workflow an (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="Bestehenden Pfad löschen und neu anlegen")

    def handle(self, *args, **options):
        reset = options["reset"]

        # ----------------------------------------------------------------
        # 1. Mängelbearbeitungs-Workflow
        # ----------------------------------------------------------------
        if reset:
            WorkflowTemplate.objects.filter(name=WORKFLOW_NAME).delete()

        wf, wf_created = WorkflowTemplate.objects.get_or_create(
            name=WORKFLOW_NAME,
            defaults={
                "beschreibung": (
                    "Bearbeitungsprozess für Betriebsmittel die bei der DGUV-V3-Prüfung "
                    "nicht bestanden haben oder bedingt bestanden haben."
                ),
                "kategorie": WorkflowTemplate.KATEGORIE_GENEHMIGUNG,
                "ist_aktiv": True,
                "ist_graph_workflow": True,
            },
        )

        if wf_created:
            ws1 = WorkflowStep.objects.create(
                template=wf, reihenfolge=1, node_id="wm01",
                titel="Mangel bewerten",
                beschreibung="Schwere des Mangels bewerten und Sofortmaßnahmen festlegen.",
                aktion_typ=WorkflowStep.AKTION_PRUEFEN,
                schritt_typ="task", pos_x=300, pos_y=80,
            )
            ws2 = WorkflowStep.objects.create(
                template=wf, reihenfolge=2, node_id="wm02",
                titel="Betriebsmittel außer Betrieb nehmen",
                beschreibung="Gerät kennzeichnen, sichern und aus dem Verkehr ziehen.",
                aktion_typ=WorkflowStep.AKTION_BEARBEITEN,
                schritt_typ="task", pos_x=300, pos_y=230,
            )
            ws3 = WorkflowStep.objects.create(
                template=wf, reihenfolge=3, node_id="wm03",
                titel="Reparatur / Ersatz veranlassen",
                beschreibung="Reparaturauftrag erteilen oder Ersatzgerät beschaffen.",
                aktion_typ=WorkflowStep.AKTION_BEARBEITEN,
                schritt_typ="task", pos_x=300, pos_y=380,
            )
            ws4 = WorkflowStep.objects.create(
                template=wf, reihenfolge=4, node_id="wm04",
                titel="Nachprüfung durchführen",
                beschreibung="Repariertes/neues Gerät erneut nach DGUV V3 prüfen.",
                aktion_typ=WorkflowStep.AKTION_PRUEFEN,
                schritt_typ="task", pos_x=300, pos_y=530,
            )
            ws5 = WorkflowStep.objects.create(
                template=wf, reihenfolge=5, node_id="wm05",
                titel="Abgeschlossen",
                beschreibung="Mangel behoben, Gerät freigegeben.",
                aktion_typ=WorkflowStep.AKTION_INFORMIEREN,
                schritt_typ="task", pos_x=300, pos_y=680,
            )
            for von, zu, label in [
                (ws1, ws2, "Außer Betrieb"),
                (ws2, ws3, "Reparatur beauftragt"),
                (ws3, ws4, "Bereit zur Nachprüfung"),
                (ws4, ws5, "Nachprüfung bestanden"),
            ]:
                WorkflowTransition.objects.create(
                    template=wf, von_schritt=von, zu_schritt=zu,
                    label=label, bedingung_typ="immer", prioritaet=1,
                )
            self.stdout.write(f"  ✓ Workflow angelegt: {WORKFLOW_NAME}")
        else:
            self.stdout.write(f"  · Workflow existiert bereits: {WORKFLOW_NAME}")

        # ----------------------------------------------------------------
        # 2. DGUV-V3-Prüfprotokoll-Pfad
        # ----------------------------------------------------------------
        if reset:
            AntrPfad.objects.filter(name=PFAD_NAME).delete()

        if AntrPfad.objects.filter(name=PFAD_NAME).exists():
            self.stdout.write(f"  · Pfad existiert bereits: {PFAD_NAME}")
            self.stdout.write(self.style.SUCCESS("\n✓ Fertig – Pfad bereits vorhanden.\n"))
            return

        pfad = AntrPfad.objects.create(
            name=PFAD_NAME,
            beschreibung=(
                "Prüfprotokoll für ortsveränderliche elektrische Betriebsmittel "
                "nach DGUV Vorschrift 3 / VDE 0701-0702. "
                "Geeignet für Elektrofachkräfte (EFK) und elektrotechnisch "
                "unterwiesene Personen (EuP)."
            ),
            aktiv=True,
            oeffentlich=False,
            kuerzel=PFAD_KUERZEL,
            kategorie="Arbeitssicherheit",
            workflow_template=wf,
        )

        # ----------------------------------------------------------------
        # Schritte
        # ----------------------------------------------------------------
        schritte_def = [

            # --------------------------------------------------------
            # s01 – Betriebsmitteldaten
            # --------------------------------------------------------
            dict(node_id="s01", titel="Betriebsmitteldaten",
                 ist_start=True, ist_ende=False, pos_x=300, pos_y=80,
                 felder_json=[
                     {"id": "hinweis_start", "typ": "textblock",
                      "text": (
                          "<strong>DGUV Vorschrift 3</strong> – Prüfprotokoll für ortsveränderliche "
                          "elektrische Betriebsmittel (§ 5 DGUV V3, VDE 0701-0702).<br>"
                          "Bitte alle Pflichtfelder (✱) ausfüllen."
                      )},
                     {"id": "bezeichnung",    "typ": "text",    "label": "Bezeichnung / Geräteart",
                      "pflicht": True,
                      "hilfetext": "z.B. Bohrmaschine, Verlängerungskabel, Laptop-Netzteil"},
                     {"id": "hersteller",     "typ": "text",    "label": "Hersteller",         "pflicht": False},
                     {"id": "typ_modell",     "typ": "text",    "label": "Typ / Modell",        "pflicht": False},
                     {"id": "seriennummer",   "typ": "text",    "label": "Seriennummer",        "pflicht": False},
                     {"id": "inventarnummer", "typ": "text",    "label": "Inventarnummer",
                      "pflicht": True,
                      "hilfetext": "Interne Gerätenummer / Anlagenkennzeichen"},
                     {"id": "standort",       "typ": "text",    "label": "Standort / Abteilung / Kostenstelle",
                      "pflicht": True},
                     {"id": "schutzklasse",   "typ": "auswahl", "label": "Schutzklasse",
                      "pflicht": True,
                      "optionen": ["Schutzklasse I (Schutzleiter)", "Schutzklasse II (Schutzisolierung)",
                                   "Schutzklasse III (Schutzkleinspannung SELV/PELV)"],
                      "hilfetext": "Steht meist auf dem Typenschild: I = Erdungszeichen, II = □ im □"},
                     {"id": "nennspannung",   "typ": "text",    "label": "Nennspannung (V)",    "pflicht": False,
                      "hilfetext": "z.B. 230 V, 400 V, 12 V"},
                     {"id": "baujahr",        "typ": "text",    "label": "Baujahr (falls bekannt)", "pflicht": False},
                     {"id": "foto_geraet",    "typ": "datei",   "label": "Foto des Betriebsmittels (optional)",
                      "pflicht": False,
                      "hilfetext": "Foto von Gerät und Typenschild empfohlen"},
                 ]),

            # --------------------------------------------------------
            # s02 – Sichtprüfung
            # --------------------------------------------------------
            dict(node_id="s02", titel="Sichtprüfung",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=230,
                 felder_json=[
                     {"id": "hinweis_sicht", "typ": "textblock",
                      "text": (
                          "Sichtprüfung gemäß VDE 0701-0702 Abschnitt 5.2. "
                          "Bewertung: <strong>i.O.</strong> = in Ordnung, "
                          "<strong>n.i.O.</strong> = nicht in Ordnung, "
                          "<strong>n.p.</strong> = nicht prüfbar / nicht vorhanden."
                      )},
                     {"id": "sp_gehaeuse",       "typ": "auswahl", "label": "Gehäuse / Schutzabdeckung",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."]},
                     {"id": "sp_kabel",          "typ": "auswahl", "label": "Anschlussleitung / Kabel",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."],
                      "hilfetext": "Auf Knicke, Quetschungen, blanke Stellen, Isolationsschäden achten"},
                     {"id": "sp_stecker",        "typ": "auswahl", "label": "Stecker / Kupplung",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."],
                      "hilfetext": "Auf Risse, verbrannte Kontakte, fehlende Schutzkontakte achten"},
                     {"id": "sp_zugentlastung",  "typ": "auswahl", "label": "Zugentlastung",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."]},
                     {"id": "sp_schalter",       "typ": "auswahl", "label": "Schalter / Bedienelemente",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."]},
                     {"id": "sp_beschriftung",   "typ": "auswahl", "label": "Beschriftung / Typenschild",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O.", "n.p."]},
                     {"id": "sp_bemerkungen",    "typ": "textarea", "label": "Bemerkungen zur Sichtprüfung",
                      "pflicht": False,
                      "hilfetext": "Auffälligkeiten beschreiben – wird ins Protokoll übernommen"},
                     {"id": "foto_mangel",       "typ": "datei",    "label": "Foto eines Mangels (falls vorhanden)",
                      "pflicht": False},
                 ]),

            # --------------------------------------------------------
            # s03a – Messtechnik Schutzklasse I
            # (wird nur bei SK I angezeigt – Transition-Logik)
            # --------------------------------------------------------
            dict(node_id="s03a", titel="Messtechnik – Schutzklasse I",
                 ist_start=False, ist_ende=False, pos_x=150, pos_y=380,
                 felder_json=[
                     {"id": "hinweis_sk1", "typ": "textblock",
                      "text": (
                          "Messungen nach VDE 0701-0702 Abschnitt 5.3 für Schutzklasse I.<br>"
                          "<strong>Grenzwerte:</strong> R<sub>PE</sub> ≤ 0,3 Ω | "
                          "R<sub>ISO</sub> ≥ 1 MΩ (bei 500 V Prüfspannung)"
                      )},
                     {"id": "pruefgeraet_typ", "typ": "text", "label": "Prüfgerät Typ / Bezeichnung",
                      "pflicht": True,
                      "hilfetext": "z.B. Benning IT 130, Metrel MI 3102 BT"},
                     {"id": "pruefgeraet_sn",  "typ": "text", "label": "Prüfgerät Seriennummer",
                      "pflicht": False},
                     {"id": "pruefspannung",   "typ": "auswahl", "label": "Prüfspannung Isolation",
                      "pflicht": True,
                      "optionen": ["500 V DC", "250 V DC (für 12/24V-Geräte)"]},
                     {"id": "rpe_wert",        "typ": "text", "label": "Schutzleiterwiderstand R_PE (Ω)",
                      "pflicht": True,
                      "hilfetext": "Grenzwert: ≤ 0,3 Ω"},
                     {"id": "rpe_bestanden",   "typ": "auswahl", "label": "R_PE – Grenzwert eingehalten?",
                      "pflicht": True, "optionen": ["Ja – i.O.", "Nein – n.i.O."]},
                     {"id": "riso_wert",       "typ": "text", "label": "Isolationswiderstand R_ISO (MΩ)",
                      "pflicht": True,
                      "hilfetext": "Grenzwert: ≥ 1 MΩ"},
                     {"id": "riso_bestanden",  "typ": "auswahl", "label": "R_ISO – Grenzwert eingehalten?",
                      "pflicht": True, "optionen": ["Ja – i.O.", "Nein – n.i.O."]},
                     {"id": "ipa_wert",        "typ": "text", "label": "Schutzleiterstrom I_PA (mA) – optional",
                      "pflicht": False,
                      "hilfetext": "Nur bei Geräten mit erhöhtem Ableitstrom erforderlich"},
                 ]),

            # --------------------------------------------------------
            # s03b – Messtechnik Schutzklasse II
            # --------------------------------------------------------
            dict(node_id="s03b", titel="Messtechnik – Schutzklasse II",
                 ist_start=False, ist_ende=False, pos_x=450, pos_y=380,
                 felder_json=[
                     {"id": "hinweis_sk2", "typ": "textblock",
                      "text": (
                          "Messungen nach VDE 0701-0702 für Schutzklasse II (Schutzisolierung).<br>"
                          "<strong>Kein Schutzleiter vorhanden</strong> – Isolationsmessung maßgeblich.<br>"
                          "Grenzwert: R<sub>ISO</sub> ≥ 2 MΩ (bei 500 V)"
                      )},
                     {"id": "sk2_pruefgeraet",  "typ": "text",    "label": "Prüfgerät Typ",       "pflicht": True},
                     {"id": "sk2_pruefgeraet_sn","typ": "text",    "label": "Prüfgerät Seriennummer", "pflicht": False},
                     {"id": "sk2_pruefspannung", "typ": "auswahl", "label": "Prüfspannung",
                      "pflicht": True, "optionen": ["500 V DC", "250 V DC"]},
                     {"id": "sk2_riso_wert",     "typ": "text",    "label": "Isolationswiderstand R_ISO (MΩ)",
                      "pflicht": True, "hilfetext": "Grenzwert: ≥ 2 MΩ"},
                     {"id": "sk2_riso_bestanden","typ": "auswahl", "label": "R_ISO – Grenzwert eingehalten?",
                      "pflicht": True, "optionen": ["Ja – i.O.", "Nein – n.i.O."]},
                     {"id": "sk2_schutziso",     "typ": "auswahl", "label": "Schutzisolierung unbeschädigt (Sichtprüfung)",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O."]},
                 ]),

            # --------------------------------------------------------
            # s03c – Schutzklasse III (keine Messung nötig)
            # --------------------------------------------------------
            dict(node_id="s03c", titel="Schutzklasse III – Prüfvermerk",
                 ist_start=False, ist_ende=False, pos_x=700, pos_y=380,
                 felder_json=[
                     {"id": "hinweis_sk3", "typ": "textblock",
                      "text": (
                          "Schutzklasse III (Schutzkleinspannung SELV/PELV) – "
                          "keine Messung des Schutzleiterwiderstands erforderlich.<br>"
                          "Sichtprüfung und Funktionskontrolle ausreichend."
                      )},
                     {"id": "sk3_versorgung",   "typ": "text",    "label": "Versorgungsspannung (V)",
                      "pflicht": True, "hilfetext": "z.B. 12 V, 24 V, 48 V"},
                     {"id": "sk3_funktion",     "typ": "auswahl", "label": "Funktion des Betriebsmittels",
                      "pflicht": True, "optionen": ["i.O.", "n.i.O."]},
                 ]),

            # --------------------------------------------------------
            # s04 – Prüfergebnis
            # --------------------------------------------------------
            dict(node_id="s04", titel="Prüfergebnis",
                 ist_start=False, ist_ende=False, pos_x=300, pos_y=530,
                 felder_json=[
                     {"id": "gesamtergebnis",   "typ": "auswahl", "label": "Gesamtergebnis der Prüfung",
                      "pflicht": True,
                      "optionen": [
                          "BESTANDEN – Betriebsmittel ist sicher (i.O.)",
                          "BEDINGT BESTANDEN – Weiterverwendung unter Auflagen möglich",
                          "NICHT BESTANDEN – Betriebsmittel außer Betrieb nehmen (n.i.O.)",
                      ]},
                     {"id": "mangelbeschreibung", "typ": "textarea",
                      "label": "Mängelbeschreibung",
                      "pflicht": False,
                      "hilfetext": "Pflichtfeld bei nicht bestandener / bedingt bestandener Prüfung"},
                     {"id": "sofortmassnahme",    "typ": "textarea",
                      "label": "Sofortmaßnahmen / empfohlene Maßnahmen",
                      "pflicht": False},
                     {"id": "pruefplakette",      "typ": "auswahl",
                      "label": "Prüfplaketten-Farbe (BGV A3 Jahresfarbe)",
                      "pflicht": False,
                      "optionen": [
                          "Grün (aktuelles Jahr)",
                          "Rot",
                          "Blau",
                          "Gelb",
                          "Keine Plakette (außer Betrieb)",
                      ]},
                     {"id": "pruefintervall",     "typ": "auswahl",
                      "label": "Nächstes Prüfintervall",
                      "pflicht": True,
                      "optionen": [
                          "6 Monate (Baustelle / erhöhte Beanspruchung)",
                          "1 Jahr (normale Beanspruchung)",
                          "2 Jahre (geringe Beanspruchung, Büro)",
                          "Nach Gefährdungsbeurteilung",
                          "Keine Nachprüfung (außer Betrieb genommen)",
                      ]},
                     {"id": "naechste_pruefung",  "typ": "datum",
                      "label": "Nächste Prüfung fällig am",
                      "pflicht": True},
                     {"id": "pruefdatum",          "typ": "datum",
                      "label": "Prüfdatum",
                      "pflicht": True},
                 ]),

            # --------------------------------------------------------
            # s05 – Prüfer / Unterschrift
            # --------------------------------------------------------
            dict(node_id="s05", titel="Prüfer & Unterschrift",
                 ist_start=False, ist_ende=True, pos_x=300, pos_y=680,
                 felder_json=[
                     {"id": "pruefer_name",       "typ": "text",    "label": "Name des Prüfers",
                      "pflicht": True},
                     {"id": "pruefer_qualifikation", "typ": "auswahl",
                      "label": "Qualifikation des Prüfers",
                      "pflicht": True,
                      "optionen": [
                          "Elektrofachkraft (EFK) nach VDE 1000-10",
                          "Elektrotechnisch unterwiesene Person (EuP) unter Aufsicht einer EFK",
                      ]},
                     {"id": "eup_hinweis", "typ": "textblock",
                      "text": (
                          "<strong>Hinweis für EuP:</strong> Als elektrotechnisch unterwiesene Person "
                          "dürfen Sie diese Prüfung nur unter Verantwortung einer Elektrofachkraft "
                          "durchführen. Bitte die verantwortliche EFK unten eintragen."
                      )},
                     {"id": "verantw_efk",  "typ": "text",
                      "label": "Verantwortliche Elektrofachkraft (nur bei EuP)",
                      "pflicht": False,
                      "hilfetext": "Name der beauftragenden/verantwortlichen EFK"},
                     {"id": "unterweisung_datum", "typ": "datum",
                      "label": "Letzte Unterweisung als EuP (nur bei EuP)",
                      "pflicht": False},
                     {"id": "firma",        "typ": "text",    "label": "Prüfende Firma / Betrieb",
                      "pflicht": False},
                     {"id": "unterschrift", "typ": "signatur", "label": "Unterschrift des Prüfers",
                      "pflicht": True},
                     {"id": "zusammenfassung", "typ": "zusammenfassung"},
                 ]),
        ]

        schritt_map = {}
        for sd in schritte_def:
            felder = sd.pop("felder_json", [])
            obj = AntrSchritt.objects.create(pfad=pfad, felder_json=felder, **sd)
            schritt_map[obj.node_id] = obj

        # ----------------------------------------------------------------
        # Transitionen
        # s01 → s02 (Sichtprüfung immer)
        # s02 → s03a (Schutzklasse I)
        # s02 → s03b (Schutzklasse II)
        # s02 → s03c (Schutzklasse III)
        # s03a/b/c → s04 (Ergebnis)
        # s04 → s05 (Unterschrift)
        # ----------------------------------------------------------------
        transitionen_def = [
            dict(von="s01", zu="s02", bedingung="", label="", reihenfolge=0),

            # Schutzklasse-Verzweigung
            dict(von="s02", zu="s03a",
                 bedingung="{{schutzklasse}} == 'Schutzklasse I (Schutzleiter)'",
                 label="SK I", reihenfolge=0),
            dict(von="s02", zu="s03b",
                 bedingung="{{schutzklasse}} == 'Schutzklasse II (Schutzisolierung)'",
                 label="SK II", reihenfolge=1),
            dict(von="s02", zu="s03c",
                 bedingung="{{schutzklasse}} == 'Schutzklasse III (Schutzkleinspannung SELV/PELV)'",
                 label="SK III", reihenfolge=2),

            # Alle Messpfade → Ergebnis
            dict(von="s03a", zu="s04", bedingung="", label="", reihenfolge=0),
            dict(von="s03b", zu="s04", bedingung="", label="", reihenfolge=0),
            dict(von="s03c", zu="s04", bedingung="", label="", reihenfolge=0),

            # Ergebnis → Unterschrift
            dict(von="s04", zu="s05", bedingung="", label="", reihenfolge=0),
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
            f"\n✓ DGUV V3 Prüfprotokoll angelegt.\n"
            f"  Pfad:     {PFAD_NAME} (PK {pfad.pk})\n"
            f"  Kürzel:   {PFAD_KUERZEL}\n"
            f"  Schritte: {len(schritte_def)}\n"
            f"  Workflow: {WORKFLOW_NAME}\n"
            f"\n"
            f"  Starten mit:\n"
            f"    docker compose exec web python manage.py dguv_v3_pfad\n"
            f"  Oder im Makefile:\n"
            f"    make dguv\n"
        ))
