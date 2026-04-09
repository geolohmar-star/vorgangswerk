# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Management Command: BAMF-Einbürgerungstest mit QuizFragenPool anlegen.

Erstellt:
  1. Einen QuizFragenPool „BAMF Einbürgerungstest" mit allen bundesweiten Fragen
  2. Einen editierbaren Pfad mit einem quizpool-Feld (30 zufällige Fragen pro Session)

Verwendung:
    python manage.py create_bamf_quiz
    python manage.py create_bamf_quiz --oeffentlich
    python manage.py create_bamf_quiz --force        # vorhandenen Pfad überschreiben
    python manage.py create_bamf_quiz --bundesland BY  # länderspezifische Fragen einschließen
"""
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Legt den BAMF-Einbürgerungstest mit QuizFragenPool (zufällig, editierbar) an."

    def add_arguments(self, parser):
        parser.add_argument("--oeffentlich", action="store_true", default=False)
        parser.add_argument("--force",       action="store_true", default=False)
        parser.add_argument("--bundesland",  default="",
                            help="2-stelliges Kürzel z.B. BY, NW – länderspezifische Fragen ergänzen")
        parser.add_argument("--anzahl",      type=int, default=30,
                            help="Anzahl zufälliger Fragen pro Session (Standard: 30)")

    def handle(self, *args, **options):
        from formulare.models import AntrPfad, AntrSchritt, AntrTransition
        from quiz.models import QuizFragenPool
        from quiz.bamf_fragen import BUNDESWEIT, LAENDER, _zu_quizfelder

        KUERZEL   = "BAMFQ"
        bundesland = options["bundesland"].upper()
        anzahl     = options["anzahl"]

        # ----------------------------------------------------------------
        # 1. QuizFragenPool erstellen oder aktualisieren
        # ----------------------------------------------------------------
        pool_name = "BAMF Einbürgerungstest – bundesweit"
        if bundesland:
            pool_name += f" + {bundesland}"

        pool, pool_neu = QuizFragenPool.objects.get_or_create(name=pool_name)

        # Pool immer mit aktuellem Katalog befüllen
        alle_fragen_roh = list(BUNDESWEIT)
        if bundesland and bundesland in LAENDER:
            alle_fragen_roh.extend(LAENDER[bundesland])
            self.stdout.write(f"  Länderfragen {bundesland}: {len(LAENDER[bundesland])} Fragen hinzugefügt")

        pool_felder = _zu_quizfelder(alle_fragen_roh, f"pool_{pool.pk if not pool_neu else 'neu'}")
        # IDs nach PK normalisieren (nach erstem Save)
        pool.fragen_json = pool_felder
        pool.save()
        # IDs mit echter PK
        for i, f in enumerate(pool.fragen_json):
            f["id"] = f"pool_{pool.pk}__{i}"
        pool.save(update_fields=["fragen_json"])

        aktion = "angelegt" if pool_neu else "aktualisiert"
        self.stdout.write(self.style.SUCCESS(
            f"QuizFragenPool '{pool.name}' (PK={pool.pk}) {aktion} – {pool.anzahl()} Fragen"
        ))

        # ----------------------------------------------------------------
        # 2. Pfad anlegen
        # ----------------------------------------------------------------
        if AntrPfad.objects.filter(kuerzel=KUERZEL).exists():
            if not options["force"]:
                self.stdout.write(self.style.WARNING(
                    f"Pfad mit Kürzel '{KUERZEL}' existiert bereits. "
                    "Benutze --force zum Überschreiben."
                ))
                return
            self.stdout.write("Lösche vorhandenen Pfad …")
            AntrPfad.objects.filter(kuerzel=KUERZEL).delete()

        with transaction.atomic():
            pfad = AntrPfad.objects.create(
                name="Einbürgerungstest (BAMF – zufällig)",
                beschreibung=(
                    f"Offizieller BAMF-Einbürgerungstest mit {anzahl} zufällig gewählten Fragen pro Session. "
                    "Bestanden ab 17 von 30 Fragen (~57 %). Jeder Durchlauf zieht eine andere Auswahl aus dem Pool."
                ),
                kuerzel=KUERZEL,
                kategorie="Quiz & Tests",
                aktiv=True,
                oeffentlich=options["oeffentlich"],
            )

            # ----------------------------------------------------------------
            # Schritt 1: Einleitung
            # ----------------------------------------------------------------
            schritt_intro = AntrSchritt.objects.create(
                pfad=pfad,
                node_id="s_intro",
                titel="Einleitung",
                ist_start=True,
                ist_ende=False,
                pos_x=200,
                pos_y=150,
                felder_json=[
                    {
                        "typ":     "textblock",
                        "id":      "intro_text",
                        "label":   "",
                        "text": (
                            "<h5>Willkommen zum Einbürgerungstest</h5>"
                            f"<p>Sie erhalten <strong>{anzahl} zufällig ausgewählte Fragen</strong> "
                            "aus dem offiziellen BAMF-Fragenkatalog. "
                            "Für das Bestehen müssen mindestens <strong>17 Fragen</strong> "
                            "richtig beantwortet werden.</p>"
                            "<p>Themen: Demokratie &amp; Grundgesetz · Geschichte · "
                            "Gesellschaft · Rechte &amp; Pflichten</p>"
                            "<em>Quelle: Bundesamt für Migration und Flüchtlinge (BAMF), "
                            "amtliches Werk nach § 5 UrhG.</em>"
                        ),
                        "pflicht": False,
                    },
                ],
            )

            # ----------------------------------------------------------------
            # Schritt 2: Quizpool (30 zufällige Fragen)
            # ----------------------------------------------------------------
            schritt_fragen = AntrSchritt.objects.create(
                pfad=pfad,
                node_id="s_fragen",
                titel="Prüfungsfragen",
                ist_start=False,
                ist_ende=False,
                pos_x=500,
                pos_y=150,
                felder_json=[
                    {
                        "typ":        "quizpool",
                        "id":         "bamf_pool",
                        "label":      "Prüfungsfragen",
                        "quelle":     "db",
                        "pool_id":    pool.pk,
                        "anzahl":     anzahl,
                        "bundesland": bundesland,
                        "pflicht":    False,
                    },
                ],
            )

            # ----------------------------------------------------------------
            # Schritt 3: Auswertung
            # ----------------------------------------------------------------
            schritt_ergebnis = AntrSchritt.objects.create(
                pfad=pfad,
                node_id="s_ergebnis",
                titel="Auswertung",
                ist_start=False,
                ist_ende=True,
                pos_x=800,
                pos_y=150,
                felder_json=[
                    {
                        "typ":                      "quizergebnis",
                        "id":                       "auswertung",
                        "label":                    "Testergebnis",
                        "bewertungsmodell":          "prozent",
                        "bestanden_ab":              57,
                        "teilpunkte":                False,
                        "zertifikat":                True,
                        "zertifikat_titel":          "Einbürgerungstest bestanden",
                        "zertifikat_gueltig_monate": 0,
                        "pflicht":                   False,
                    },
                ],
            )

            # ----------------------------------------------------------------
            # Transitionen
            # ----------------------------------------------------------------
            for von, zu in [
                (schritt_intro,   schritt_fragen),
                (schritt_fragen,  schritt_ergebnis),
            ]:
                AntrTransition.objects.create(
                    pfad=pfad,
                    von_schritt=von,
                    zu_schritt=zu,
                    bedingung="",
                    label="",
                    reihenfolge=0,
                )

        self.stdout.write(self.style.SUCCESS(
            f"\nPfad '{pfad.name}' erfolgreich angelegt!\n"
            f"  PK:        {pfad.pk}\n"
            f"  Kürzel:    {KUERZEL}\n"
            f"  Pool:      {pool.name} ({pool.anzahl()} Fragen)\n"
            f"  Pro Test:  {anzahl} zufällige Fragen\n"
            f"  Öffentlich: {'Ja' if pfad.oeffentlich else 'Nein'}\n"
            f"  Editor:    /formulare/editor/{pfad.pk}/\n"
            f"  Starten:   /formulare/starten/{pfad.pk}/"
        ))
