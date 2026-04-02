# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Formular-Pfad-System: Intelligente, verzweigte Antragsformulare.

Jeder AntrPfad ist ein gerichteter Graph:
- AntrSchritt    = Knoten  (eine Formularseite mit Feldern)
- AntrTransition = Kante   (bedingte Verbindung zwischen Schritten)

Laufende Nutzersitzungen werden in AntrSitzung verfolgt.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class AntrPfad(models.Model):
    """Definition eines verzweigten Antragsformulars."""

    aktiv = models.BooleanField(default=True, verbose_name="Aktiv")
    beschreibung = models.TextField(blank=True, verbose_name="Beschreibung")
    erstellt_am = models.DateTimeField(auto_now_add=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erstellte_pfade",
    )
    geaendert_am = models.DateTimeField(auto_now=True)
    kategorie = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Kategorie",
        help_text="Gruppe fuer die Uebersicht, z.B. 'Steuern', 'Lizenzen'",
    )
    kuerzel = models.CharField(
        max_length=6,
        blank=True,
        verbose_name="Kuerzel",
        help_text="2-6 Grossbuchstaben fuer Vorgangsnummern, z.B. HUN",
    )
    name = models.CharField(max_length=200, verbose_name="Name")
    oeffentlich = models.BooleanField(
        default=False,
        verbose_name="Oeffentlich",
        help_text="Wenn aktiv, kann dieser Pfad ohne Login ausgefuellt werden",
    )
    variablen_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Variablen",
        help_text="Pfad-weite Berechnungsgrundlagen",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Antrags-Pfad"
        verbose_name_plural = "Antrags-Pfade"

    def __str__(self):
        return self.name

    def start_schritt(self):
        """Gibt den Start-Schritt zurueck."""
        return self.schritte.filter(ist_start=True).first()


class AntrSchritt(models.Model):
    """Ein Schritt (Knoten) im Antrags-Pfad – entspricht einer Formularseite."""

    felder_json = models.JSONField(
        default=list,
        verbose_name="Felder",
        help_text="Eingabefelder dieses Schritts im Schema-Format",
    )
    ist_ende = models.BooleanField(default=False, verbose_name="End-Knoten")
    ist_start = models.BooleanField(default=False, verbose_name="Start-Knoten")
    node_id = models.CharField(max_length=50, verbose_name="Node-ID")
    pfad = models.ForeignKey(
        AntrPfad, on_delete=models.CASCADE, related_name="schritte"
    )
    pos_x = models.FloatField(default=200, verbose_name="Position X")
    pos_y = models.FloatField(default=200, verbose_name="Position Y")
    titel = models.CharField(max_length=200, verbose_name="Titel")

    class Meta:
        ordering = ["pk"]
        verbose_name = "Antrags-Schritt"
        verbose_name_plural = "Antrags-Schritte"
        unique_together = [("pfad", "node_id")]

    def __str__(self):
        return f"{self.pfad.name} \u2192 {self.titel}"

    def felder(self):
        """Gibt felder_json als Liste zurueck (sicherer Getter)."""
        return self.felder_json if isinstance(self.felder_json, list) else []


class AntrTransition(models.Model):
    """Gerichtete Kante zwischen zwei Schritten, optional mit Bedingung."""

    bedingung = models.TextField(
        blank=True,
        verbose_name="Bedingung",
        help_text="Formel-Bedingung (leer = immer wahr). Referenziert Feld-IDs.",
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Beschriftung",
        help_text="Optionaler Text auf der Kante, z.B. 'Ja'",
    )
    pfad = models.ForeignKey(
        AntrPfad, on_delete=models.CASCADE, related_name="transitionen"
    )
    reihenfolge = models.IntegerField(
        default=0,
        verbose_name="Reihenfolge",
        help_text="Auswertungsreihenfolge bei mehreren Ausgaengen (niedrig = zuerst)",
    )
    von_schritt = models.ForeignKey(
        AntrSchritt,
        on_delete=models.CASCADE,
        related_name="ausgaende",
        verbose_name="Von",
    )
    zu_schritt = models.ForeignKey(
        AntrSchritt,
        on_delete=models.CASCADE,
        related_name="eingaenge",
        verbose_name="Zu",
    )

    class Meta:
        ordering = ["reihenfolge", "pk"]
        verbose_name = "Transition"
        verbose_name_plural = "Transitionen"

    def __str__(self):
        bed = f" [{self.bedingung[:30]}]" if self.bedingung else ""
        return f"{self.von_schritt.titel} \u2192 {self.zu_schritt.titel}{bed}"


class AntrSitzung(models.Model):
    """Laufende oder abgeschlossene Nutzersitzung durch einen Antrags-Pfad."""

    STATUS_LAUFEND = "laufend"
    STATUS_ABGESCHLOSSEN = "abgeschlossen"
    STATUS_ABGEBROCHEN = "abgebrochen"

    STATUS_CHOICES = [
        (STATUS_LAUFEND, "Laufend"),
        (STATUS_ABGESCHLOSSEN, "Abgeschlossen"),
        (STATUS_ABGEBROCHEN, "Abgebrochen"),
    ]

    abgeschlossen_am = models.DateTimeField(null=True, blank=True)
    aktueller_schritt = models.ForeignKey(
        AntrSchritt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aktive_sitzungen",
    )
    besuchte_schritte = models.JSONField(
        default=list, verbose_name="Besuchte Schritte"
    )
    einwilligungen_json = models.JSONField(
        default=dict,
        verbose_name="Einwilligungen (DSGVO)",
        help_text="Protokoll erteilter Einwilligungen mit Zeitstempel",
    )
    email_anonym = models.EmailField(
        blank=True,
        null=True,
        verbose_name="E-Mail (anonym)",
    )
    gesammelte_daten = models.JSONField(default=dict, verbose_name="Gesammelte Daten")
    gestartet_am = models.DateTimeField(auto_now_add=True)
    pfad = models.ForeignKey(
        AntrPfad, on_delete=models.PROTECT, related_name="sitzungen"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_LAUFEND
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="antr_sitzungen",
    )
    vorgangsnummer = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        verbose_name="Vorgangsnummer",
        help_text="Automatisch generiert beim Abschluss, z.B. HUN-00001-20260328-1423",
    )

    class Meta:
        ordering = ["-gestartet_am"]
        verbose_name = "Antrags-Sitzung"
        verbose_name_plural = "Antrags-Sitzungen"

    def __str__(self):
        wer = str(self.user) if self.user else (self.email_anonym or "anonym")
        return f"{wer} \u2013 {self.pfad.name} ({self.get_status_display()})"

    @staticmethod
    def generiere_vorgangsnummer(pfad):
        """Erzeugt eine eindeutige Vorgangsnummer im Format KUERZEL-LFDNR-DATUM-UHRZEIT."""
        kuerzel = (pfad.kuerzel or "ANT").upper().strip()
        jetzt = timezone.localtime()
        letzte = AntrSitzung.objects.filter(
            vorgangsnummer__startswith=kuerzel + "-"
        ).order_by("-pk").first()
        if letzte and letzte.vorgangsnummer:
            try:
                lfd = int(letzte.vorgangsnummer.split("-")[1]) + 1
            except (IndexError, ValueError):
                lfd = 1
        else:
            lfd = 1
        return f"{kuerzel}-{lfd:05d}-{jetzt.strftime('%Y%m%d')}-{jetzt.strftime('%H%M')}"

    def abschliessen(self):
        """Markiert die Sitzung als abgeschlossen und generiert die Vorgangsnummer."""
        self.status = self.STATUS_ABGESCHLOSSEN
        self.abgeschlossen_am = timezone.now()
        if not self.vorgangsnummer:
            self.vorgangsnummer = AntrSitzung.generiere_vorgangsnummer(self.pfad)
        self.save(update_fields=["status", "abgeschlossen_am", "vorgangsnummer"])


class AntrDatei(models.Model):
    """Hochgeladene Datei einer Sitzung (einfacher Datei-Speicher)."""

    dateiname = models.CharField(max_length=255)
    feld_id = models.CharField(max_length=100, verbose_name="Feld-ID")
    hochgeladen_am = models.DateTimeField(auto_now_add=True)
    inhalt = models.BinaryField()
    mime_type = models.CharField(max_length=100, default="application/octet-stream")
    sitzung = models.ForeignKey(
        AntrSitzung, on_delete=models.CASCADE, related_name="dateien"
    )

    class Meta:
        ordering = ["-hochgeladen_am"]
        verbose_name = "Antrags-Datei"
        verbose_name_plural = "Antrags-Dateien"

    def __str__(self):
        return f"{self.sitzung} \u2013 {self.dateiname}"


class AntrVersion(models.Model):
    """Versionierter Snapshot eines AntrPfads (wird beim Speichern angelegt)."""

    MAX_VERSIONEN = 20

    erstellt_am = models.DateTimeField(auto_now_add=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="antr_pfad_versionen",
    )
    kommentar = models.CharField(max_length=200, blank=True)
    pfad = models.ForeignKey(
        AntrPfad, on_delete=models.CASCADE, related_name="versionen"
    )
    snapshot_json = models.JSONField(verbose_name="Snapshot")
    version_nr = models.PositiveIntegerField(verbose_name="Version")

    class Meta:
        ordering = ["-version_nr"]
        verbose_name = "Pfad-Version"
        verbose_name_plural = "Pfad-Versionen"
        unique_together = [("pfad", "version_nr")]

    def __str__(self):
        return f"{self.pfad.name} v{self.version_nr}"
