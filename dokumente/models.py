# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Dokumente-App Modelle: Einfaches DMS mit Collabora-WOPI-Unterstuetzung."""
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class DokumentKategorie(models.Model):
    """Hierarchische Kategorie fuer Dokumente."""

    beschreibung = models.TextField(blank=True, verbose_name="Beschreibung")
    elternkategorie = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="unterkategorien",
        verbose_name="Elternkategorie",
    )
    name = models.CharField(max_length=100, verbose_name="Name")
    sortierung = models.IntegerField(default=0, verbose_name="Sortierung")

    class Meta:
        ordering = ["sortierung", "name"]
        verbose_name = "Dokumentkategorie"
        verbose_name_plural = "Dokumentkategorien"

    def __str__(self):
        if self.elternkategorie:
            return f"{self.elternkategorie.name} / {self.name}"
        return self.name


class DokumentTag(models.Model):
    """Schlagwort fuer Dokumente."""

    farbe = models.CharField(
        max_length=7,
        default="#6c757d",
        verbose_name="Farbe (Hex)",
        help_text="z.B. #1a4d2e",
    )
    name = models.CharField(max_length=50, unique=True, verbose_name="Name")

    class Meta:
        ordering = ["name"]
        verbose_name = "Dokumenttag"
        verbose_name_plural = "Dokumenttags"

    def __str__(self):
        return self.name


class Dokument(models.Model):
    """Hauptmodell fuer Dokumente mit Versionierung und WOPI-Token."""

    dateiname = models.CharField(max_length=255, verbose_name="Dateiname")
    dateityp = models.CharField(max_length=100, blank=True, verbose_name="Dateityp (MIME)")
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="erstellte_dokumente",
        verbose_name="Erstellt von",
    )
    geaendert_am = models.DateTimeField(auto_now=True, verbose_name="Geaendert am")
    groesse_bytes = models.BigIntegerField(default=0, verbose_name="Groesse (Bytes)")
    gueltig_bis = models.DateField(null=True, blank=True, verbose_name="Gueltig bis")
    inhalt = models.BinaryField(verbose_name="Dateiinhalt")
    kategorie = models.ForeignKey(
        DokumentKategorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dokumente",
        verbose_name="Kategorie",
    )
    tags = models.ManyToManyField(
        DokumentTag,
        blank=True,
        related_name="dokumente",
        verbose_name="Tags",
    )
    titel = models.CharField(max_length=255, verbose_name="Titel")
    version = models.IntegerField(default=1, verbose_name="Version")
    # WOPI-Token fuer Collabora-Session (kurzlebig, 1 Stunde)
    wopi_token = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="WOPI-Token",
    )
    wopi_token_ablauf = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="WOPI-Token Ablauf",
    )

    class Meta:
        ordering = ["-geaendert_am"]
        verbose_name = "Dokument"
        verbose_name_plural = "Dokumente"
        indexes = [
            models.Index(fields=["dateiname"]),
            models.Index(fields=["erstellt_von", "erstellt_am"]),
        ]

    def __str__(self):
        return f"{self.titel} (v{self.version})"

    @property
    def groesse_lesbar(self):
        """Menschenlesbare Dateigroesse."""
        groesse = self.groesse_bytes
        for einheit in ["B", "KB", "MB", "GB"]:
            if groesse < 1024:
                return f"{groesse:.0f} {einheit}"
            groesse /= 1024
        return f"{groesse:.1f} TB"

    @property
    def ist_office_dokument(self):
        """Prueft ob das Dokument in Collabora editierbar ist."""
        editierbare_typen = {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.ms-powerpoint",
        }
        return self.dateityp in editierbare_typen

    @property
    def ist_pdf(self):
        return self.dateityp == "application/pdf"

    @property
    def ist_bild(self):
        return self.dateityp.startswith("image/")

    def erstelle_wopi_token(self):
        """Erzeugt einen neuen kurzlebigen WOPI-Token (1 Stunde gueltig)."""
        self.wopi_token = secrets.token_hex(32)
        self.wopi_token_ablauf = timezone.now() + timedelta(hours=1)
        self.save(update_fields=["wopi_token", "wopi_token_ablauf"])
        return self.wopi_token

    def wopi_token_gueltig(self):
        """Prueft ob der aktuelle WOPI-Token noch gueltig ist."""
        if not self.wopi_token or not self.wopi_token_ablauf:
            return False
        return timezone.now() < self.wopi_token_ablauf


class DokumentVersion(models.Model):
    """Archivierte Version eines Dokuments."""

    dokument = models.ForeignKey(
        Dokument,
        on_delete=models.CASCADE,
        related_name="versionen",
        verbose_name="Dokument",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Erstellt von",
    )
    groesse_bytes = models.BigIntegerField(default=0, verbose_name="Groesse (Bytes)")
    inhalt = models.BinaryField(verbose_name="Dateiinhalt")
    kommentar = models.CharField(max_length=255, blank=True, verbose_name="Kommentar")
    version_nr = models.IntegerField(verbose_name="Versionsnummer")

    class Meta:
        ordering = ["-version_nr"]
        unique_together = [("dokument", "version_nr")]
        verbose_name = "Dokumentversion"
        verbose_name_plural = "Dokumentversionen"

    def __str__(self):
        return f"{self.dokument.titel} – v{self.version_nr}"


class ZugriffsProtokoll(models.Model):
    """Unveraenderbares Zugriffsprotokoll (DSGVO Art. 5 Abs. 2)."""

    AKTION_DOWNLOAD = "download"
    AKTION_VORSCHAU = "vorschau"
    AKTION_ERSTELLT = "erstellt"
    AKTION_GEAENDERT = "geaendert"
    AKTION_GELOESCHT = "geloescht"
    AKTION_COLLABORA = "collabora_bearbeitet"
    AKTION_VERSION = "version_wiederhergestellt"
    AKTION_UPLOAD = "hochgeladen"

    AKTION_CHOICES = [
        (AKTION_DOWNLOAD, "Heruntergeladen"),
        (AKTION_VORSCHAU, "Vorschau"),
        (AKTION_ERSTELLT, "Erstellt"),
        (AKTION_GEAENDERT, "Geaendert"),
        (AKTION_GELOESCHT, "Geloescht"),
        (AKTION_COLLABORA, "In Collabora bearbeitet"),
        (AKTION_VERSION, "Version wiederhergestellt"),
        (AKTION_UPLOAD, "Hochgeladen"),
    ]

    aktion = models.CharField(max_length=30, choices=AKTION_CHOICES, verbose_name="Aktion")
    dokument = models.ForeignKey(
        Dokument,
        on_delete=models.SET_NULL,
        null=True,
        related_name="protokolle",
        verbose_name="Dokument",
    )
    dokument_titel = models.CharField(
        max_length=255,
        verbose_name="Dokumenttitel",
        help_text="Sicherungskopie fuer geloeschte Dokumente",
    )
    ip_adresse = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP-Adresse")
    notiz = models.CharField(max_length=255, blank=True, verbose_name="Notiz")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Benutzer",
    )
    zeitpunkt = models.DateTimeField(auto_now_add=True, verbose_name="Zeitpunkt")

    class Meta:
        ordering = ["-zeitpunkt"]
        verbose_name = "Zugriffsprotokoll"
        verbose_name_plural = "Zugriffsprotokolle"

    def __str__(self):
        user_str = self.user.username if self.user else "unbekannt"
        return f"{self.get_aktion_display()} – {self.dokument_titel} – {user_str}"

    def save(self, *args, **kwargs):
        """Verhindert Veraenderung bestehender Eintraege."""
        if self.pk:
            raise PermissionError("ZugriffsProtokoll-Eintraege duerfen nicht veraendert werden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("ZugriffsProtokoll-Eintraege duerfen nicht geloescht werden.")
