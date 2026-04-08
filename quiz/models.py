# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Quiz-App – Models: QuizErgebnis, QuizZertifikat.

Jede abgeschlossene Antragssitzung mit quizergebnis-Feld bekommt
genau ein QuizErgebnis. Bei Bestehen + Zertifikat-Konfiguration
wird zusätzlich ein QuizZertifikat (PDF) erzeugt.
"""
import uuid as _uuid

from django.db import models


class QuizErgebnis(models.Model):
    MODELL_PROZENT       = "prozent"
    MODELL_NOTEN         = "noten"
    MODELL_PUNKTE        = "punkte"
    MODELL_FUEHRERSCHEIN = "fuehrerschein"

    uuid = models.UUIDField(default=_uuid.uuid4, unique=True, editable=False)
    sitzung = models.OneToOneField(
        "formulare.AntrSitzung",
        on_delete=models.CASCADE,
        related_name="quiz_ergebnis",
    )
    punkte_erreicht  = models.DecimalField(max_digits=8, decimal_places=2)
    punkte_gesamt    = models.DecimalField(max_digits=8, decimal_places=2)
    fehlerpunkte     = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    prozent          = models.DecimalField(max_digits=5, decimal_places=2)
    bestanden        = models.BooleanField()
    note             = models.CharField(max_length=10, blank=True)   # "1" – "6"
    note_text        = models.CharField(max_length=40, blank=True)   # "Sehr gut"
    bewertungsmodell = models.CharField(max_length=20)
    # Detailauswertung pro Frage: {frage_id: {antwort, korrekt, punkte, fehlerpunkte}}
    antworten_json   = models.JSONField(default=dict)
    # Snapshot der quizergebnis-Feld-Konfiguration
    config_snapshot  = models.JSONField(default=dict)
    erstellt_am      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Quiz-Ergebnis"
        verbose_name_plural = "Quiz-Ergebnisse"
        ordering            = ["-erstellt_am"]

    def __str__(self):
        status = "bestanden" if self.bestanden else "nicht bestanden"
        return f"Sitzung #{self.sitzung_id} – {self.prozent} % – {status}"

    @property
    def prozent_int(self):
        return int(self.prozent)


class QuizZertifikat(models.Model):
    ergebnis = models.OneToOneField(
        QuizErgebnis,
        on_delete=models.CASCADE,
        related_name="zertifikat",
    )
    pdf_inhalt          = models.BinaryField()
    erstellt_am         = models.DateTimeField(auto_now_add=True)
    ablaufdatum         = models.DateField(null=True, blank=True)
    erinnerung_gesendet = models.BooleanField(default=False)

    class Meta:
        verbose_name        = "Quiz-Zertifikat"
        verbose_name_plural = "Quiz-Zertifikate"

    def __str__(self):
        return f"Zertifikat – {self.ergebnis}"
