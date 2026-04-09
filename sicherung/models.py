# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Sicherungs-Protokoll – BSI CON.3 Datensicherungskonzept.

Jede Sicherung wird mit SHA-256-Prüfsumme und Metadaten protokolliert.
Aufbewahrungsfristen: 7 täglich / 4 wöchentlich / 12 monatlich.
"""
from django.db import models


class SicherungsProtokoll(models.Model):
    TYP_DATENBANK = "datenbank"
    TYP_DATEIEN   = "dateien"
    TYP_KOMPLETT  = "komplett"
    TYP_CHOICES = [
        (TYP_DATENBANK, "Datenbank (PostgreSQL)"),
        (TYP_DATEIEN,   "Statische Dateien"),
        (TYP_KOMPLETT,  "Komplett"),
    ]

    RHYTHMUS_TAEGLICH    = "taeglich"
    RHYTHMUS_WOECHENTLICH = "woechentlich"
    RHYTHMUS_MONATLICH   = "monatlich"
    RHYTHMUS_MANUELL     = "manuell"
    RHYTHMUS_CHOICES = [
        (RHYTHMUS_TAEGLICH,     "Täglich"),
        (RHYTHMUS_WOECHENTLICH, "Wöchentlich"),
        (RHYTHMUS_MONATLICH,    "Monatlich"),
        (RHYTHMUS_MANUELL,      "Manuell"),
    ]

    STATUS_OK      = "ok"
    STATUS_FEHLER  = "fehler"
    STATUS_GEPRUEFT = "geprueft"
    STATUS_CHOICES = [
        (STATUS_OK,      "Erfolgreich"),
        (STATUS_FEHLER,  "Fehler"),
        (STATUS_GEPRUEFT, "Geprüft & OK"),
    ]

    typ              = models.CharField(max_length=20, choices=TYP_CHOICES)
    rhythmus         = models.CharField(max_length=20, choices=RHYTHMUS_CHOICES, default=RHYTHMUS_MANUELL)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)
    dateiname        = models.CharField(max_length=255)
    dateipfad        = models.CharField(max_length=500)
    groesse_bytes    = models.BigIntegerField(default=0)
    sha256_pruefsumme = models.CharField(max_length=64, blank=True)
    verschluesselt   = models.BooleanField(default=True)
    fehlermeldung    = models.TextField(blank=True)
    erstellt_am      = models.DateTimeField(auto_now_add=True)
    geprueft_am      = models.DateTimeField(null=True, blank=True)
    geloescht_am     = models.DateTimeField(null=True, blank=True)
    erstellt_von     = models.CharField(max_length=100, default="system")

    class Meta:
        verbose_name = "Sicherungsprotokoll"
        verbose_name_plural = "Sicherungsprotokolle"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.dateiname} [{self.status}] {self.erstellt_am:%d.%m.%Y %H:%M}"

    @property
    def groesse_lesbar(self):
        b = self.groesse_bytes
        for einheit in ["B", "KB", "MB", "GB"]:
            if b < 1024:
                return f"{b:.1f} {einheit}"
            b /= 1024
        return f"{b:.1f} TB"
