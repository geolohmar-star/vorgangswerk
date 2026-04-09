"""Korrespondenz-App – Briefvorlagen und Briefvorgaenge.

Briefvorlage: DOCX-Datei mit {{platzhalter}} gespeichert in der DB.
Briefvorgang: Befuellter Brief, editierbar in Collabora Online.
"""
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Firmendaten(models.Model):
    """Globale Absender- und Fusszeilen-Daten fuer alle Briefvorlagen (Singleton)."""

    firmenname  = models.CharField(max_length=200, blank=True, verbose_name="Firmenname / Behoerde")
    strasse     = models.CharField(max_length=200, blank=True, verbose_name="Strasse / Hausnummer")
    plz_ort     = models.CharField(max_length=100, blank=True, verbose_name="PLZ / Ort")
    telefon     = models.CharField(max_length=50,  blank=True, verbose_name="Telefon")
    telefax     = models.CharField(max_length=50,  blank=True, verbose_name="Telefax")
    email       = models.CharField(max_length=200, blank=True, verbose_name="E-Mail")
    internet    = models.CharField(max_length=200, blank=True, verbose_name="Internet")
    ort         = models.CharField(max_length=100, blank=True, verbose_name="Ort (fuer Datumszeile)")
    grussformel = models.CharField(max_length=200, blank=True, default="Mit freundlichen Gruessen",
                                   verbose_name="Standard-Grussformel")

    class Meta:
        verbose_name        = "Firmendaten"
        verbose_name_plural = "Firmendaten"

    def __str__(self):
        return self.firmenname or "Firmendaten"

    @classmethod
    def laden(cls):
        """Gibt den einzigen Datensatz zurueck; erstellt ihn bei Bedarf."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Bankverbindung(models.Model):
    """Bankverbindungen der Organisation – verwaltbar nur durch Admins."""
    kuerzel       = models.SlugField(max_length=50, unique=True, verbose_name="Kürzel",
                                     help_text="Kleinbuchstaben/Ziffern/Bindestrich, z.B. 'hauptkonto'")
    bezeichnung   = models.CharField(max_length=200, verbose_name="Bezeichnung")
    kontoinhaber  = models.CharField(max_length=200, blank=True, verbose_name="Kontoinhaber")
    iban          = models.CharField(max_length=34,  blank=True, verbose_name="IBAN")
    bic           = models.CharField(max_length=11,  blank=True, verbose_name="BIC")
    bank_name     = models.CharField(max_length=200, blank=True, verbose_name="Bank")
    reihenfolge   = models.PositiveSmallIntegerField(default=0, verbose_name="Reihenfolge")

    class Meta:
        verbose_name        = "Bankverbindung"
        verbose_name_plural = "Bankverbindungen"
        ordering            = ["reihenfolge", "bezeichnung"]

    def __str__(self):
        return self.bezeichnung

    def als_variablen(self):
        """Gibt dict mit allen Variablen dieser Bankverbindung zurück."""
        return {
            f"bank_{self.kuerzel}_iban":         self.iban,
            f"bank_{self.kuerzel}_bic":          self.bic,
            f"bank_{self.kuerzel}_bank":         self.bank_name,
            f"bank_{self.kuerzel}_kontoinhaber": self.kontoinhaber,
            f"bank_{self.kuerzel}_bezeichnung":  self.bezeichnung,
        }


class Briefvorlage(models.Model):
    """DOCX-Vorlage mit {{platzhalter}} fuer Geschaeftsbriefe.

    Platzhalter der Form {{schluessel}} werden beim Erstellen eines
    Briefvorgangs durch echte Werte ersetzt.
    """

    titel        = models.CharField(max_length=200, verbose_name="Titel")
    beschreibung = models.TextField(blank=True, verbose_name="Beschreibung")
    inhalt       = models.BinaryField(verbose_name="DOCX-Inhalt")
    ist_aktiv    = models.BooleanField(default=True, verbose_name="Aktiv")
    ist_standard = models.BooleanField(
        default=False,
        verbose_name="Standard-Vorlage",
        help_text="Wird beim neuen Brief automatisch vorausgewaehlt.",
    )
    version      = models.PositiveIntegerField(default=1, verbose_name="Version")

    # Verknuepfung mit einem Formular-Pfad (Kuerzel) – ermoeglicht Bescheid-Erstellung
    pfad_kuerzel = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Pfad-Kuerzel",
        help_text="Kuerzel des Formular-Pfads (z. B. HUND). Wenn gesetzt, wird diese Vorlage "
                  "beim Bescheid-Generator fuer diesen Pfad angeboten.",
    )
    gruppe = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Gruppe",
        help_text="Optionaler Gruppenname innerhalb des Pfads.",
    )

    # Standard-Absender (wird beim Erstellen eines Briefs vorbelegt)
    default_absender_name    = models.CharField(max_length=200, blank=True, verbose_name="Standard-Absender Name")
    default_absender_strasse = models.CharField(max_length=200, blank=True, verbose_name="Standard-Absender Strasse")
    default_absender_ort     = models.CharField(max_length=200, blank=True, verbose_name="Standard-Absender PLZ/Ort")
    default_absender_telefon = models.CharField(max_length=50,  blank=True, verbose_name="Standard-Absender Telefon")
    default_absender_email   = models.CharField(max_length=200, blank=True, verbose_name="Standard-Absender E-Mail")
    default_ort              = models.CharField(max_length=100, blank=True, verbose_name="Standard-Ort (Datum-Zeile)")
    default_grussformel      = models.CharField(max_length=200, blank=True, verbose_name="Standard-Grussformel")

    # Fusszeile
    fusszeile_firmenname = models.CharField(max_length=200, blank=True, verbose_name="Fusszeile Firmenname")
    fusszeile_telefon    = models.CharField(max_length=50,  blank=True, verbose_name="Fusszeile Telefon")
    fusszeile_telefax    = models.CharField(max_length=50,  blank=True, verbose_name="Fusszeile Telefax")
    fusszeile_email      = models.CharField(max_length=200, blank=True, verbose_name="Fusszeile E-Mail")
    fusszeile_internet   = models.CharField(max_length=200, blank=True, verbose_name="Fusszeile Internet")

    # OnlyOffice Doc-Key (eindeutiger Cache-Key pro Bearbeitungssitzung)
    doc_key           = models.CharField(max_length=100, blank=True, default="", verbose_name="OO Doc-Key")
    # WOPI-Token fuer Collabora (veraltet, wird nicht mehr verwendet)
    wopi_token        = models.CharField(max_length=64, blank=True, default="", verbose_name="WOPI-Token")
    wopi_token_ablauf = models.DateTimeField(null=True, blank=True, verbose_name="WOPI-Token Ablauf")

    erstellt_am  = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    erstellt_von = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="briefvorlagen", verbose_name="Erstellt von",
    )

    class Meta:
        ordering = ["titel"]
        verbose_name = "Briefvorlage"
        verbose_name_plural = "Briefvorlagen"

    def __str__(self):
        return self.titel

    def erstelle_wopi_token(self) -> str:
        """Gibt bestehenden gueltigen Token zurueck oder generiert neuen."""
        # Frisch aus DB lesen um Race-Conditions zu vermeiden
        fresh = Briefvorlage.objects.values("wopi_token", "wopi_token_ablauf").get(pk=self.pk)
        if fresh["wopi_token"] and fresh["wopi_token_ablauf"] and timezone.now() < fresh["wopi_token_ablauf"]:
            return fresh["wopi_token"]
        token = secrets.token_hex(32)
        ablauf = timezone.now() + timedelta(hours=1)
        Briefvorlage.objects.filter(pk=self.pk).update(wopi_token=token, wopi_token_ablauf=ablauf)
        self.wopi_token = token
        self.wopi_token_ablauf = ablauf
        return token


class Briefvorgang(models.Model):
    """Einzelner Briefvorgang – befuellte Vorlage, editierbar in Collabora."""

    STATUS_ENTWURF    = "entwurf"
    STATUS_FERTIG     = "fertig"
    STATUS_ARCHIVIERT = "archiviert"
    STATUS_CHOICES = [
        (STATUS_ENTWURF,    "Entwurf"),
        (STATUS_FERTIG,     "Fertig"),
        (STATUS_ARCHIVIERT, "Archiviert"),
    ]

    vorlage = models.ForeignKey(
        Briefvorlage, on_delete=models.PROTECT, related_name="vorgaenge",
        verbose_name="Vorlage",
    )

    # Absender
    absender_name    = models.CharField(max_length=200, verbose_name="Absender Name")
    absender_strasse = models.CharField(max_length=200, blank=True, verbose_name="Absender Strasse")
    absender_ort     = models.CharField(max_length=200, blank=True, verbose_name="Absender PLZ/Ort")
    absender_telefon = models.CharField(max_length=50,  blank=True, verbose_name="Absender Telefon")
    absender_email   = models.CharField(max_length=200, blank=True, verbose_name="Absender E-Mail")

    # Empfaenger
    empfaenger_name    = models.CharField(max_length=200, verbose_name="Empfaenger Name")
    empfaenger_zusatz  = models.CharField(max_length=200, blank=True, verbose_name="Empfaenger Zusatz")
    empfaenger_strasse = models.CharField(max_length=200, blank=True, verbose_name="Empfaenger Strasse")
    empfaenger_plz_ort = models.CharField(max_length=200, blank=True, verbose_name="Empfaenger PLZ/Ort")
    empfaenger_land    = models.CharField(max_length=200, blank=True, verbose_name="Empfaenger Land")

    # Briefinhalt
    ort              = models.CharField(max_length=100, verbose_name="Ort")
    datum            = models.DateField(verbose_name="Datum")
    betreff          = models.CharField(max_length=300, verbose_name="Betreff")
    anrede           = models.CharField(max_length=200, blank=True, verbose_name="Anrede")
    brieftext        = models.TextField(blank=True, verbose_name="Brieftext")
    grussformel      = models.CharField(max_length=200, default="Mit freundlichen Gruessen", verbose_name="Grussformel")
    unterschrift_name  = models.CharField(max_length=200, verbose_name="Unterzeichner")
    unterschrift_titel = models.CharField(max_length=200, blank=True, verbose_name="Funktion/Titel")

    # Verknuepfung mit Formular-Sitzung
    sitzung = models.ForeignKey(
        "formulare.AntrSitzung",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="briefe",
        verbose_name="Formular-Sitzung",
    )

    # Verknuepfung mit Workflow-Task (wenn aus Task-Bearbeitung erstellt)
    workflow_task = models.ForeignKey(
        "workflow.WorkflowTask",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="briefe",
        verbose_name="Workflow-Task",
    )

    # Bearbeiter-Signatur (FES nach OO-Bearbeitung)
    bearbeiter_signiert_von = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bearbeitete_briefe", verbose_name="Bearbeitet und signiert von",
    )
    bearbeiter_signiert_am = models.DateTimeField(null=True, blank=True, verbose_name="Signiert am")
    signiert_pdf = models.BinaryField(null=True, blank=True, verbose_name="Signiertes PDF")

    # DOCX-Inhalt (nach Befuellung und Collabora-Bearbeitung)
    inhalt  = models.BinaryField(null=True, blank=True, verbose_name="DOCX-Inhalt")
    version = models.PositiveIntegerField(default=1, verbose_name="Version")

    # Collabora WOPI-Token
    wopi_token       = models.CharField(max_length=64, blank=True, default="", verbose_name="WOPI-Token")
    wopi_token_ablauf = models.DateTimeField(null=True, blank=True, verbose_name="WOPI-Token Ablauf")

    # Status und Metadaten
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ENTWURF, verbose_name="Status")
    erstellt_von = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="briefe", verbose_name="Erstellt von",
    )
    erstellt_am  = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    geaendert_am = models.DateTimeField(auto_now=True, verbose_name="Geaendert am")

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Briefvorgang"
        verbose_name_plural = "Briefvorgaenge"

    def __str__(self):
        return f"{self.datum} – {self.betreff}"

    def erstelle_wopi_token(self) -> str:
        """Gibt bestehenden gueltigen Token zurueck oder generiert neuen."""
        fresh = Briefvorgang.objects.values("wopi_token", "wopi_token_ablauf").get(pk=self.pk)
        if fresh["wopi_token"] and fresh["wopi_token_ablauf"] and timezone.now() < fresh["wopi_token_ablauf"]:
            return fresh["wopi_token"]
        token = secrets.token_hex(32)
        ablauf = timezone.now() + timedelta(hours=1)
        Briefvorgang.objects.filter(pk=self.pk).update(wopi_token=token, wopi_token_ablauf=ablauf)
        self.wopi_token = token
        self.wopi_token_ablauf = ablauf
        return token

    def wopi_token_gueltig(self) -> bool:
        if not self.wopi_token_ablauf:
            return False
        return timezone.now() < self.wopi_token_ablauf
