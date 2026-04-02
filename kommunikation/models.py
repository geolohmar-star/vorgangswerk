# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Kommunikation-App Modelle: Eingehende E-Mails, Anhaenge, Benachrichtigungen."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class EingehendeEmail(models.Model):
    """Eingehende E-Mail aus dem IMAP-Postfach."""

    STATUS_NEU = "neu"
    STATUS_GELESEN = "gelesen"
    STATUS_ARCHIVIERT = "archiviert"
    STATUS_ZUGEWIESEN = "zugewiesen"

    STATUS_CHOICES = [
        (STATUS_NEU, "Neu"),
        (STATUS_GELESEN, "Gelesen"),
        (STATUS_ARCHIVIERT, "Archiviert"),
        (STATUS_ZUGEWIESEN, "Zugewiesen"),
    ]

    absender_email = models.EmailField(verbose_name="Absender (E-Mail)")
    absender_name = models.CharField(max_length=255, blank=True, verbose_name="Absender (Name)")
    betreff = models.CharField(max_length=500, blank=True, verbose_name="Betreff")
    empfangen_am = models.DateTimeField(verbose_name="Empfangen am")
    empfaenger_email = models.EmailField(blank=True, verbose_name="Empfaenger (E-Mail)")
    importiert_am = models.DateTimeField(auto_now_add=True, verbose_name="Importiert am")
    inhalt_html = models.TextField(blank=True, verbose_name="Inhalt (HTML)")
    inhalt_text = models.TextField(blank=True, verbose_name="Inhalt (Text)")
    # RFC 2822 Message-ID zur Deduplizierung
    message_id = models.CharField(
        max_length=500,
        unique=True,
        verbose_name="Message-ID",
        help_text="RFC 2822 Message-ID zur Deduplizierung",
    )
    notiz = models.TextField(blank=True, verbose_name="Interne Notiz")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_NEU,
        verbose_name="Status",
    )
    zugewiesen_an = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zugewiesene_emails",
        verbose_name="Zugewiesen an",
    )

    class Meta:
        ordering = ["-empfangen_am"]
        verbose_name = "Eingehende E-Mail"
        verbose_name_plural = "Eingehende E-Mails"
        indexes = [
            models.Index(fields=["status", "empfangen_am"]),
            models.Index(fields=["absender_email"]),
        ]

    def __str__(self):
        return f"{self.betreff or '(kein Betreff)'} von {self.absender_email}"

    @property
    def ist_neu(self):
        return self.status == self.STATUS_NEU

    @property
    def hat_anhaenge(self):
        return self.anhaenge.exists()


class EmailAnhang(models.Model):
    """Anhang einer eingehenden E-Mail."""

    dateiname = models.CharField(max_length=255, verbose_name="Dateiname")
    dateityp = models.CharField(max_length=100, blank=True, verbose_name="MIME-Typ")
    email = models.ForeignKey(
        EingehendeEmail,
        on_delete=models.CASCADE,
        related_name="anhaenge",
        verbose_name="E-Mail",
    )
    groesse_bytes = models.BigIntegerField(default=0, verbose_name="Groesse (Bytes)")
    inhalt = models.BinaryField(verbose_name="Dateiinhalt")

    class Meta:
        ordering = ["dateiname"]
        verbose_name = "E-Mail-Anhang"
        verbose_name_plural = "E-Mail-Anhaenge"

    def __str__(self):
        return f"{self.dateiname} ({self.email})"

    @property
    def groesse_lesbar(self):
        groesse = self.groesse_bytes
        for einheit in ["B", "KB", "MB"]:
            if groesse < 1024:
                return f"{groesse:.0f} {einheit}"
            groesse /= 1024
        return f"{groesse:.1f} GB"


class Benachrichtigung(models.Model):
    """System-Benachrichtigung fuer einen Benutzer.

    Wird z.B. bei faelligen Workflow-Tasks oder eingehenden Antraegen erzeugt.
    """

    TYP_INFO = "info"
    TYP_WARNUNG = "warnung"
    TYP_AUFGABE = "aufgabe"
    TYP_EMAIL = "email"

    TYP_CHOICES = [
        (TYP_INFO, "Information"),
        (TYP_WARNUNG, "Warnung"),
        (TYP_AUFGABE, "Aufgabe"),
        (TYP_EMAIL, "Neue E-Mail"),
    ]

    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    gelesen = models.BooleanField(default=False, verbose_name="Gelesen")
    gelesen_am = models.DateTimeField(null=True, blank=True, verbose_name="Gelesen am")
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Link",
        help_text="URL-Pfad zum verknuepften Objekt",
    )
    nachricht = models.TextField(verbose_name="Nachricht")
    titel = models.CharField(max_length=255, verbose_name="Titel")
    typ = models.CharField(
        max_length=20,
        choices=TYP_CHOICES,
        default=TYP_INFO,
        verbose_name="Typ",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="benachrichtigungen",
        verbose_name="Empfaenger",
    )

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Benachrichtigung"
        verbose_name_plural = "Benachrichtigungen"
        indexes = [
            models.Index(fields=["user", "gelesen", "erstellt_am"]),
        ]

    def __str__(self):
        return f"{self.user.username}: {self.titel}"

    def als_gelesen_markieren(self):
        if not self.gelesen:
            self.gelesen = True
            self.gelesen_am = timezone.now()
            self.save(update_fields=["gelesen", "gelesen_am"])

    @classmethod
    def erstelle(cls, user, titel, nachricht, typ=TYP_INFO, link=""):
        """Hilfsmethode zum Erstellen einer Benachrichtigung."""
        return cls.objects.create(
            user=user,
            titel=titel,
            nachricht=nachricht,
            typ=typ,
            link=link,
        )
