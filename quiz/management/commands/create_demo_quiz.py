# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management Command: Demo-Quiz „Einbürgerungstest" anlegen.

Legt einen vollständigen, lauffähigen Pfad mit 30 Fragen aus dem BAMF-
Fragenkatalog an. Bereits vorhandene Pfade mit demselben Kürzel werden
übersprungen (idempotent).

Verwendung:
    python manage.py create_demo_quiz
    python manage.py create_demo_quiz --oeffentlich
    python manage.py create_demo_quiz --force   # vorhandenen Pfad überschreiben
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Legt den Demo-Quiz 'Einbürgerungstest (BAMF)' als Pfad an."

    def add_arguments(self, parser):
        parser.add_argument(
            "--oeffentlich",
            action="store_true",
            default=False,
            help="Pfad als öffentlich (ohne Login ausfüllbar) markieren",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Vorhandenen Pfad mit demselben Kürzel vorher löschen",
        )

    def handle(self, *args, **options):
        from formulare.models import AntrPfad, AntrSchritt, AntrTransition
        from quiz.einbuergerungstest import get_fragen_als_felder

        KUERZEL = "EINB"

        if AntrPfad.objects.filter(kuerzel=KUERZEL).exists():
            if not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f"Pfad mit Kürzel '{KUERZEL}' existiert bereits. "
                    "Benutze --force zum Überschreiben."
                ))
                return
            self.stdout.write("Lösche vorhandenen Pfad …")
            AntrPfad.objects.filter(kuerzel=KUERZEL).delete()

        fragen = get_fragen_als_felder(anzahl=None)  # alle 30

        with transaction.atomic():
            pfad = AntrPfad.objects.create(
                name="Einbürgerungstest (Demo)",
                beschreibung=(
                    "Offizieller Einbürgerungstest des Bundesamts für Migration und Flüchtlinge (BAMF). "
                    "30 Multiple-Choice-Fragen zu Grundgesetz, Demokratie und deutscher Geschichte. "
                    "Bestanden ab 17/30 richtigen Antworten (~57 %)."
                ),
                kuerzel=KUERZEL,
                kategorie="Demo",
                aktiv=True,
                oeffentlich=options["oeffentlich"],
            )

            # ----------------------------------------------------------------
            # Schritt 1: Einleitung
            # ----------------------------------------------------------------
            intro_felder = [
                {
                    "typ":   "textblock",
                    "id":    "intro_text",
                    "label": "Willkommen zum Einbürgerungstest",
                    "text": (
                        "<p>Dieser Test prüft Ihre Kenntnisse über das Leben in Deutschland. "
                        "Der offizielle Einbürgerungstest besteht aus <strong>33 Fragen</strong>, "
                        "von denen mindestens <strong>17 richtig</strong> beantwortet werden müssen.</p>"
                        "<p>Diese Demo enthält <strong>30 Fragen</strong> aus dem offiziellen "
                        "BAMF-Fragenkatalog. Beantworten Sie jede Frage sorgfältig – "
                        "Sie können nicht zurückgehen.</p>"
                        "<p><em>Quelle: Bundesamt für Migration und Flüchtlinge (BAMF), "
                        "amtliches Werk nach § 5 UrhG.</em></p>"
                    ),
                    "pflicht": False,
                },
            ]

            schritt_intro = AntrSchritt.objects.create(
                pfad=pfad,
                node_id="s_intro",
                titel="Einleitung",
                ist_start=True,
                ist_ende=False,
                felder_json=intro_felder,
                pos_x=200,
                pos_y=100,
            )

            # ----------------------------------------------------------------
            # Schritt 2–4: Fragen aufgeteilt auf je ~10 pro Seite
            # ----------------------------------------------------------------
            blaetter = [fragen[0:10], fragen[10:20], fragen[20:30]]
            blatt_schritte = []

            for i, blatt in enumerate(blaetter, start=1):
                s = AntrSchritt.objects.create(
                    pfad=pfad,
                    node_id=f"s_fragen_{i}",
                    titel=f"Fragen {(i - 1) * 10 + 1}–{i * 10}",
                    ist_start=False,
                    ist_ende=False,
                    felder_json=blatt,
                    pos_x=200 + i * 250,
                    pos_y=100,
                )
                blatt_schritte.append(s)

            # ----------------------------------------------------------------
            # Schritt 5: Auswertung
            # ----------------------------------------------------------------
            ergebnis_felder = [
                {
                    "typ":               "quizergebnis",
                    "id":                "auswertung",
                    "label":             "Ihr Testergebnis",
                    "bewertungsmodell":  "prozent",
                    "bestanden_ab":      57,
                    "teilpunkte":        False,
                    "zertifikat":        True,
                    "zertifikat_titel":  "Einbürgerungstest bestanden",
                    "zertifikat_gueltig_monate": 0,
                    "pflicht":           False,
                },
            ]

            schritt_ergebnis = AntrSchritt.objects.create(
                pfad=pfad,
                node_id="s_ergebnis",
                titel="Auswertung",
                ist_start=False,
                ist_ende=True,
                felder_json=ergebnis_felder,
                pos_x=200 + 4 * 250,
                pos_y=100,
            )

            # ----------------------------------------------------------------
            # Transitionen: intro → blatt1 → blatt2 → blatt3 → ergebnis
            # ----------------------------------------------------------------
            alle_schritte = [schritt_intro] + blatt_schritte + [schritt_ergebnis]
            for von, zu in zip(alle_schritte, alle_schritte[1:]):
                AntrTransition.objects.create(
                    pfad=pfad,
                    von_schritt=von,
                    zu_schritt=zu,
                    bedingung="",
                    label="",
                    reihenfolge=0,
                )

        self.stdout.write(self.style.SUCCESS(
            f"Pfad '{pfad.name}' (PK={pfad.pk}, Kürzel={KUERZEL}) erfolgreich angelegt.\n"
            f"  Schritte: {AntrSchritt.objects.filter(pfad=pfad).count()}\n"
            f"  Fragen:   {len(fragen)}\n"
            f"  Öffentlich: {'Ja' if pfad.oeffentlich else 'Nein'}\n"
            f"  URL: /formulare/editor/{pfad.pk}/"
        ))
