# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Posteintrag(models.Model):
    RICHTUNG_EINGANG = "eingang"
    RICHTUNG_AUSGANG = "ausgang"
    RICHTUNG_CHOICES = [
        (RICHTUNG_EINGANG, "Eingang"),
        (RICHTUNG_AUSGANG, "Ausgang"),
    ]

    TYP_BRIEF = "brief"
    TYP_EMAIL = "email"
    TYP_FAX = "fax"
    TYP_PAKET = "paket"
    TYP_INTERN = "intern"
    TYP_SONSTIGES = "sonstiges"
    TYP_CHOICES = [
        (TYP_BRIEF, "Brief"),
        (TYP_EMAIL, "E-Mail"),
        (TYP_FAX, "Fax"),
        (TYP_PAKET, "Paket / Einschreiben"),
        (TYP_INTERN, "Interne Post"),
        (TYP_SONSTIGES, "Sonstiges"),
    ]

    # Tagebuchnummer: JJJJ-NNNN (wird automatisch gesetzt)
    lfd_nr = models.CharField(
        max_length=20, unique=True, blank=True, verbose_name="Tagebuch-Nr."
    )
    datum = models.DateField(default=timezone.now, verbose_name="Datum")
    richtung = models.CharField(
        max_length=10, choices=RICHTUNG_CHOICES, verbose_name="Richtung"
    )
    typ = models.CharField(
        max_length=20, choices=TYP_CHOICES, default=TYP_BRIEF, verbose_name="Typ"
    )
    absender_empfaenger = models.CharField(
        max_length=300, verbose_name="Absender / Empfaenger"
    )
    betreff = models.CharField(max_length=500, verbose_name="Betreff")
    vorgang_bezug = models.CharField(
        max_length=200, blank=True, verbose_name="Vorgangsbezug / Aktenzeichen"
    )
    notiz = models.TextField(blank=True, verbose_name="Interne Notiz")

    # Optionale Verknüpfungen
    dokument = models.ForeignKey(
        "dokumente.Dokument",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="posteintraege",
        verbose_name="Dokument",
    )
    eingehende_email = models.OneToOneField(
        "kommunikation.EingehendeEmail",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="posteintrag",
        verbose_name="Eingehende E-Mail",
    )
    briefvorgang = models.OneToOneField(
        "korrespondenz.Briefvorgang",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="posteintrag",
        verbose_name="Briefvorgang",
    )

    erstellt_von = models.ForeignKey(
        User, null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="posteintraege",
        verbose_name="Erstellt von",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    geaendert_am = models.DateTimeField(auto_now=True, verbose_name="Geaendert am")

    class Meta:
        ordering = ["-datum", "-lfd_nr"]
        verbose_name = "Posteintrag"
        verbose_name_plural = "Postbuch"
        indexes = [
            models.Index(fields=["datum"]),
            models.Index(fields=["richtung", "datum"]),
        ]

    def __str__(self):
        return f"{self.lfd_nr} – {self.absender_empfaenger}: {self.betreff}"

    def save(self, *args, **kwargs):
        if not self.lfd_nr:
            self.lfd_nr = _naechste_lfd_nr(self.datum)
        super().save(*args, **kwargs)

    @property
    def richtung_icon(self):
        return "&#8594;" if self.richtung == self.RICHTUNG_AUSGANG else "&#8592;"


class Organisation(models.Model):
    """Einfaches Verzeichnis von Behoerden und Meldestellen – kein Buerger-CRM."""

    TYP_BEHOERDE   = "behoerde"
    TYP_POLIZEI    = "polizei"
    TYP_GERICHT    = "gericht"
    TYP_GEMEINDE   = "gemeinde"
    TYP_SONSTIGE   = "sonstige"
    TYP_CHOICES = [
        (TYP_BEHOERDE, "Behörde"),
        (TYP_POLIZEI,  "Polizei / Strafverfolgung"),
        (TYP_GERICHT,  "Gericht"),
        (TYP_GEMEINDE, "Gemeinde / Stadt"),
        (TYP_SONSTIGE, "Sonstige Institution"),
    ]

    name    = models.CharField(max_length=200, verbose_name="Name / Bezeichnung")
    typ     = models.CharField(max_length=20, choices=TYP_CHOICES, default=TYP_BEHOERDE, verbose_name="Typ")
    email   = models.EmailField(blank=True, verbose_name="E-Mail")
    telefon = models.CharField(max_length=50, blank=True, verbose_name="Telefon")
    fax     = models.CharField(max_length=50, blank=True, verbose_name="Fax")
    strasse = models.CharField(max_length=200, blank=True, verbose_name="Straße / Hausnummer")
    plz     = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    ort     = models.CharField(max_length=100, blank=True, verbose_name="Ort")
    notiz   = models.TextField(blank=True, verbose_name="Interne Notiz")
    erstellt_am  = models.DateTimeField(auto_now_add=True)
    geaendert_am = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisationsverzeichnis"

    def __str__(self):
        return self.name

    @property
    def adresse_einzeilig(self):
        teile = [self.strasse, f"{self.plz} {self.ort}".strip()]
        return ", ".join(t for t in teile if t)


class VerteilEmpfaenger(models.Model):
    """Einzelner Empfaenger eines Verteiler-Schritts mit Quittierungsstatus."""

    TYP_EMAIL = "email"
    TYP_BRIEF = "brief"
    TYP_CHOICES = [
        (TYP_EMAIL, "E-Mail"),
        (TYP_BRIEF, "Brief / manuell"),
    ]

    STATUS_AUSSTEHEND = "ausstehend"
    STATUS_VERSENDET  = "versendet"
    STATUS_BESTAETIGT = "bestaetigt"
    STATUS_MANUELL    = "manuell"
    STATUS_CHOICES = [
        (STATUS_AUSSTEHEND, "Ausstehend"),
        (STATUS_VERSENDET,  "Versendet"),
        (STATUS_BESTAETIGT, "Bestaetigt"),
        (STATUS_MANUELL,    "Manuell erledigt"),
    ]

    workflow_task = models.ForeignKey(
        "workflow.WorkflowTask",
        on_delete=models.CASCADE,
        related_name="verteiler",
        verbose_name="Workflow-Task",
    )
    name  = models.CharField(max_length=200, verbose_name="Empfaenger-Bezeichnung")
    email = models.EmailField(blank=True, verbose_name="E-Mail-Adresse")
    typ   = models.CharField(max_length=10, choices=TYP_CHOICES, default=TYP_EMAIL)

    token        = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AUSSTEHEND)
    versendet_am  = models.DateTimeField(null=True, blank=True, verbose_name="Versendet am")
    bestaetigt_am = models.DateTimeField(null=True, blank=True, verbose_name="Bestaetigt am")
    bestaetigung_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP bei Bestaetigung")
    notiz        = models.TextField(blank=True, verbose_name="Notiz")
    erstellt_am  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["erstellt_am"]
        verbose_name = "Verteiler-Empfaenger"
        verbose_name_plural = "Verteiler-Empfaenger"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    @property
    def ist_erledigt(self):
        return self.status in (self.STATUS_BESTAETIGT, self.STATUS_MANUELL)

    @property
    def status_farbe(self):
        return {
            self.STATUS_AUSSTEHEND: "secondary",
            self.STATUS_VERSENDET:  "warning",
            self.STATUS_BESTAETIGT: "success",
            self.STATUS_MANUELL:    "info",
        }.get(self.status, "secondary")


def _naechste_lfd_nr(datum=None):
    """Erzeugt naechste Tagebuchnummer im Format JJJJ-NNNN."""
    from django.db.models import Max
    import re
    jahr = (datum or timezone.now().date()).year
    prefix = f"{jahr}-"
    letzter = (
        Posteintrag.objects.filter(lfd_nr__startswith=prefix)
        .aggregate(m=Max("lfd_nr"))["m"]
    )
    if letzter:
        match = re.search(r"-(\d+)$", letzter)
        naechste = int(match.group(1)) + 1 if match else 1
    else:
        naechste = 1
    return f"{jahr}-{naechste:04d}"
