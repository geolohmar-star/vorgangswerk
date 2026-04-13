# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management-Command: Demo-Daten laden.

Legt einen Demo-Benutzer, einen Beispiel-Pfad (Hundesteuer-Anmeldung)
und einen Beispiel-Workflow an. Sicher mehrfach ausführbar (idempotent).

Nutzung:
    python manage.py demo_daten
    python manage.py demo_daten --reset   # bestehende Demo-Daten löschen und neu anlegen
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from formulare.models import AntrPfad, AntrSchritt, AntrTransition
from workflow.models import WorkflowStep, WorkflowTemplate, WorkflowTransition

User = get_user_model()

DEMO_EMAIL = "demo@vorgangswerk.de"
DEMO_PASSWORD = "Demo1234!"

PFAD_NAME = "Hundesteuer – Anmeldung"
WORKFLOW_NAME = "Hundesteuer – Bearbeitungsprozess"


class Command(BaseCommand):
    help = "Lädt Demo-Daten: Benutzer, Beispiel-Pfad, Beispiel-Workflow"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Bestehende Demo-Daten löschen und neu anlegen",
        )

    def handle(self, *args, **options):
        reset = options["reset"]

        # ----------------------------------------------------------------
        # 1. Demo-Benutzer
        # ----------------------------------------------------------------
        if reset:
            User.objects.filter(email=DEMO_EMAIL).delete()

        user, created = User.objects.get_or_create(
            email=DEMO_EMAIL,
            defaults={
                "username": "demo",
                "first_name": "Maria",
                "last_name": "Mustermann",
                "is_staff": False,
                "is_active": True,
            },
        )
        if created or reset:
            user.set_password(DEMO_PASSWORD)
            user.save()
            self.stdout.write(f"  ✓ Demo-Benutzer angelegt: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            self.stdout.write(f"  · Demo-Benutzer existiert bereits: {DEMO_EMAIL}")

        # ----------------------------------------------------------------
        # 2. Beispiel-Workflow (Hundesteuer-Bearbeitungsprozess)
        # ----------------------------------------------------------------
        if reset:
            WorkflowTemplate.objects.filter(name=WORKFLOW_NAME).delete()

        wf_template, wf_created = WorkflowTemplate.objects.get_or_create(
            name=WORKFLOW_NAME,
            defaults={
                "beschreibung": "Bearbeitungsprozess für eingegangene Hundesteuer-Anmeldungen.",
                "kategorie": WorkflowTemplate.KATEGORIE_GENEHMIGUNG,
                "ist_aktiv": True,
                "ist_graph_workflow": True,
            },
        )

        if wf_created:
            ws1 = WorkflowStep.objects.create(
                template=wf_template,
                titel="Antrag prüfen",
                beschreibung="Eingegangenen Antrag auf Vollständigkeit und Richtigkeit prüfen.",
                aktion_typ=WorkflowStep.AKTION_PRUEFEN,
                schritt_typ="task",
                reihenfolge=1,
                node_id="ws01",
                pos_x=300,
                pos_y=80,
            )
            ws2 = WorkflowStep.objects.create(
                template=wf_template,
                titel="Steuerbescheid erstellen",
                beschreibung="Steuerbescheid ausfüllen und dem Bürger zusenden.",
                aktion_typ=WorkflowStep.AKTION_BEARBEITEN,
                schritt_typ="task",
                reihenfolge=2,
                node_id="ws02",
                pos_x=300,
                pos_y=230,
            )
            ws3 = WorkflowStep.objects.create(
                template=wf_template,
                titel="Abgeschlossen",
                beschreibung="Vorgang ist abgeschlossen.",
                aktion_typ=WorkflowStep.AKTION_INFORMIEREN,
                schritt_typ="task",
                reihenfolge=3,
                node_id="ws03",
                pos_x=300,
                pos_y=380,
            )
            WorkflowTransition.objects.create(
                template=wf_template,
                von_schritt=ws1,
                zu_schritt=ws2,
                label="Vollständig",
                bedingung_typ="immer",
                prioritaet=1,
            )
            WorkflowTransition.objects.create(
                template=wf_template,
                von_schritt=ws2,
                zu_schritt=ws3,
                label="Bescheid versandt",
                bedingung_typ="immer",
                prioritaet=1,
            )
            self.stdout.write(f"  ✓ Workflow-Template angelegt: {WORKFLOW_NAME} (PK {wf_template.pk})")
        else:
            self.stdout.write(f"  · Workflow-Template existiert bereits: {WORKFLOW_NAME}")

        # ----------------------------------------------------------------
        # 3. Beispiel-Pfad (Hundesteuer-Anmeldung)
        # ----------------------------------------------------------------
        if reset:
            AntrPfad.objects.filter(name=PFAD_NAME).delete()

        if AntrPfad.objects.filter(name=PFAD_NAME).exists():
            self.stdout.write(f"  · Pfad existiert bereits: {PFAD_NAME}")
        else:
            pfad = AntrPfad.objects.create(
                name=PFAD_NAME,
                beschreibung=(
                    "Anmeldung eines Hundes zur Hundesteuer. "
                    "Bitte alle Angaben vollständig ausfüllen."
                ),
                aktiv=True,
                oeffentlich=True,
                kuerzel="HUN",
                kategorie="Steuern",
                leika_schluessel="99108018026000",
                workflow_template=wf_template,
            )

            schritte_def = [

                # ------------------------------------------------------------
                # s01 – Angaben zur Person
                # ------------------------------------------------------------
                dict(node_id="s01", titel="Angaben zur Person",
                     ist_start=True, ist_ende=False, pos_x=300, pos_y=80,
                     felder_json=[
                         {"id": "anrede",    "typ": "radio",   "label": "Anrede",     "pflicht": True,
                          "optionen": ["Herr", "Frau", "Divers"]},
                         {"id": "vorname",   "typ": "text",    "label": "Vorname",    "pflicht": True,  "fim_id": "F60000003"},
                         {"id": "nachname",  "typ": "text",    "label": "Nachname",   "pflicht": True,  "fim_id": "F60000004"},
                         {"id": "strasse",   "typ": "text",    "label": "Straße, Haus-Nr.", "pflicht": True, "fim_id": "F60000022"},
                         {"id": "plz",       "typ": "plz",     "label": "Postleitzahl",     "pflicht": True, "fim_id": "F60000024"},
                         {"id": "ort",       "typ": "text",    "label": "Wohnort",          "pflicht": True, "fim_id": "F60000025"},
                         {"id": "telefon",   "typ": "telefon", "label": "Telefonnummer",    "pflicht": False, "fim_id": "F60000031"},
                         {"id": "email",     "typ": "email",   "label": "E-Mail-Adresse",   "pflicht": False, "fim_id": "F60000030"},
                     ]),

                # ------------------------------------------------------------
                # s02 – Angaben zum Hund
                # ------------------------------------------------------------
                dict(node_id="s02", titel="Angaben zum Hund",
                     ist_start=False, ist_ende=False, pos_x=300, pos_y=230,
                     felder_json=[
                         {"id": "hundename",     "typ": "text",  "label": "Name des Hundes",  "pflicht": True},
                         {"id": "rasse",         "typ": "text",  "label": "Rasse",            "pflicht": True},
                         {"id": "geburtsdatum",  "typ": "datum", "label": "Geburtsdatum des Hundes", "pflicht": True},
                         {"id": "geschlecht",    "typ": "radio", "label": "Geschlecht",       "pflicht": True,
                          "optionen": ["männlich", "weiblich"]},
                         {"id": "farbe",         "typ": "text",  "label": "Fellfarbe",        "pflicht": False},
                         {"id": "chip_nummer",   "typ": "text",  "label": "Chip-Nummer (15-stellig)", "pflicht": False,
                          "hilfetext": "Transponder-Nummer aus dem EU-Heimtierausweis"},
                         {"id": "haltung_seit",  "typ": "datum", "label": "In Haltung seit",  "pflicht": True,
                          "hilfetext": "Datum ab dem der Hund in Ihrem Haushalt lebt"},
                     ]),

                # ------------------------------------------------------------
                # s03 – Besondere Umstände
                # ------------------------------------------------------------
                dict(node_id="s03", titel="Besondere Umstände",
                     ist_start=False, ist_ende=False, pos_x=300, pos_y=380,
                     felder_json=[
                         {"id": "hinweis_ermaessigung", "typ": "textblock",
                          "text": "Unter bestimmten Voraussetzungen besteht Anspruch auf Steuerermäßigung "
                                  "(z.B. für Blindenführhunde, Rettungshunde oder Hunde aus dem Tierheim)."},
                         {"id": "ist_kampfhund",   "typ": "bool", "label": "Es handelt sich um einen als gefährlich eingestuften Hund (Listenhund)"},
                         {"id": "ist_blindenhund", "typ": "bool", "label": "Es handelt sich um einen Assistenz- oder Blindenführhund"},
                         {"id": "ist_tierheim",    "typ": "bool", "label": "Der Hund stammt aus einem Tierheim"},
                         {"id": "weitere_hunde",   "typ": "bool", "label": "Im Haushalt leben weitere steuerpflichtige Hunde"},
                     ]),

                # ------------------------------------------------------------
                # s03b – Listenhund-Details (NUR bei Kampfhund)
                # ------------------------------------------------------------
                dict(node_id="s03b", titel="Listenhund – Pflichtangaben",
                     ist_start=False, ist_ende=False, pos_x=700, pos_y=380,
                     felder_json=[
                         {"id": "kampfhund_hinweis", "typ": "textblock",
                          "text": "Für als gefährlich eingestufte Hunde gelten erhöhte Steuersätze "
                                  "und besondere Auflagen gemäß der Gefahrhundeverordnung."},
                         {"id": "kampfhund_erlaubnis", "typ": "bool",
                          "label": "Eine Erlaubnis zur Haltung des Listenhundes liegt vor"},
                         {"id": "kampfhund_aktenzeichen", "typ": "text",
                          "label": "Aktenzeichen der Haltungserlaubnis", "pflicht": True},
                     ]),

                # ------------------------------------------------------------
                # s04 – Einwilligung & Unterschrift (ENDE)
                # ------------------------------------------------------------
                dict(node_id="s04", titel="Einwilligung & Abschluss",
                     ist_start=False, ist_ende=True, pos_x=300, pos_y=530,
                     felder_json=[
                         {"id": "einwilligung_daten", "typ": "einwilligung",
                          "text": "Ich erkläre, dass die gemachten Angaben der Wahrheit entsprechen. "
                                  "Ich bin mir bewusst, dass unrichtige Angaben strafrechtliche Folgen haben können.",
                          "pflicht": True},
                         {"id": "datum",        "typ": "datum",    "label": "Datum",          "pflicht": True, "fim_id": "F60000060"},
                         {"id": "unterschrift", "typ": "signatur", "label": "Unterschrift",   "pflicht": True},
                         {"id": "zusammenfassung", "typ": "zusammenfassung"},
                     ]),
            ]

            schritt_map = {}
            for sd in schritte_def:
                felder = sd.pop("felder_json", [])
                obj = AntrSchritt.objects.create(pfad=pfad, felder_json=felder, **sd)
                schritt_map[obj.node_id] = obj

            transitionen_def = [
                dict(von="s01", zu="s02", bedingung="", label="", reihenfolge=0),
                dict(von="s02", zu="s03", bedingung="", label="", reihenfolge=0),
                # Listenhund-Zweig
                dict(von="s03", zu="s03b",
                     bedingung="{{ist_kampfhund}} == '1'",
                     label="Listenhund", reihenfolge=0),
                dict(von="s03", zu="s04", bedingung="", label="", reihenfolge=1),
                dict(von="s03b", zu="s04", bedingung="", label="", reihenfolge=0),
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

            self.stdout.write(
                f"  ✓ Pfad angelegt: {PFAD_NAME} (PK {pfad.pk})\n"
                f"    {len(schritte_def)} Schritte | {len(transitionen_def)} Transitionen\n"
                f"    Öffentliche URL: /formulare/antrag/{pfad.pk}/"
            )

        # ----------------------------------------------------------------
        # Zusammenfassung
        # ----------------------------------------------------------------
        self.stdout.write(self.style.SUCCESS(
            "\n✓ Demo-Daten bereit.\n"
            f"  Benutzer:  {DEMO_EMAIL}  /  {DEMO_PASSWORD}\n"
            f"  Pfad:      {PFAD_NAME}\n"
            f"  Workflow:  {WORKFLOW_NAME}\n"
        ))
