# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Datenschutz-Modelle: Löschprotokoll für DSGVO-Nachweise (Art. 5 Abs. 2 DSGVO).
"""
from django.db import models
from django.utils import timezone


class Loeschprotokoll(models.Model):
    """Dauerhaftes Protokoll über durchgeführte Datenlöschungen.

    Enthält ausschließlich Metadaten – KEINE personenbezogenen Inhalte mehr.
    Nur ein anonymisierter Namensstumpf und die interne User-ID bleiben als
    Nachweis für Aufsichtsbehörden erhalten (Art. 5 Abs. 2 DSGVO).
    """

    user_id_intern = models.IntegerField(
        verbose_name="Interne User-ID (war)",
        help_text="PK des gelöschten Django-Users – kein FK mehr.",
    )
    benutzername_kuerzel = models.CharField(
        max_length=10,
        verbose_name="Benutzername-Kürzel",
        help_text="Erste 5 Zeichen des Benutzernamens zur Identifikation.",
    )
    email_kuerzel = models.CharField(
        max_length=20,
        verbose_name="E-Mail-Kürzel",
        help_text="Erste 3 Zeichen + Domain-Teil der E-Mail.",
        blank=True,
    )
    loeschung_ausgefuehrt_am = models.DateTimeField(default=timezone.now)
    loeschung_durch = models.CharField(
        max_length=200,
        verbose_name="Ausgeführt durch",
    )
    kategorien = models.JSONField(
        verbose_name="Gelöschte Datenkategorien",
        help_text="Dict: Kategoriename → Anzahl Datensätze.",
        default=dict,
    )
    protokoll_pdf = models.BinaryField(
        null=True, blank=True,
        verbose_name="Protokoll-PDF",
    )

    class Meta:
        ordering = ["-loeschung_ausgefuehrt_am"]
        verbose_name = "Löschprotokoll"
        verbose_name_plural = "Löschprotokolle"

    def __str__(self):
        return (
            f"Löschung {self.benutzername_kuerzel}*** "
            f"am {self.loeschung_ausgefuehrt_am.date()}"
        )
