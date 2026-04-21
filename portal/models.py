# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Portal-Modelle: Prepaid-Konten, Analyse-Jobs, Transaktionen.
"""
import secrets
from django.db import models
from django.contrib.auth.models import User


class PortalAccount(models.Model):
    """Prepaid-Konto eines Portal-Nutzers."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="portal_account")
    credits = models.IntegerField(default=0)
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    email_verifiziert = models.BooleanField(default=False)
    verifikations_token = models.CharField(max_length=64, blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Portal-Konto"
        verbose_name_plural = "Portal-Konten"

    def __str__(self):
        return f"{self.user.email} ({self.credits} Credits)"

    def neues_verifikations_token(self):
        self.verifikations_token = secrets.token_urlsafe(32)
        self.save(update_fields=["verifikations_token"])
        return self.verifikations_token

    def credit_gutschreiben(self, anzahl: int, beschreibung: str, stripe_pi: str = ""):
        self.credits += anzahl
        self.save(update_fields=["credits"])
        CreditTransaktion.objects.create(
            account=self,
            typ="kauf",
            betrag=anzahl,
            beschreibung=beschreibung,
            stripe_payment_intent=stripe_pi,
        )

    def credit_abziehen(self, anzahl: int, beschreibung: str):
        """Zieht Credits ab. Gibt False zurück wenn nicht genug Credits."""
        if self.credits < anzahl:
            return False
        self.credits -= anzahl
        self.save(update_fields=["credits"])
        CreditTransaktion.objects.create(
            account=self,
            typ="verbrauch",
            betrag=-anzahl,
            beschreibung=beschreibung,
        )
        return True


class FormularAnalyse(models.Model):
    """Analyse-Job: PDF hochgeladen → Claude analysiert → Pfad-JSON."""
    STATUS_WARTEND = "wartend"
    STATUS_VERARBEITUNG = "verarbeitung"
    STATUS_FERTIG = "fertig"
    STATUS_FEHLER = "fehler"
    STATUS_IMPORTIERT = "importiert"

    STATUS_CHOICES = [
        (STATUS_WARTEND, "Wartend"),
        (STATUS_VERARBEITUNG, "In Verarbeitung"),
        (STATUS_FERTIG, "Fertig"),
        (STATUS_FEHLER, "Fehler"),
        (STATUS_IMPORTIERT, "Importiert"),
    ]

    account = models.ForeignKey(PortalAccount, on_delete=models.CASCADE, related_name="analysen")
    dateiname = models.CharField(max_length=255)
    pdf_inhalt = models.BinaryField()
    pdf_original = models.BinaryField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WARTEND)
    ergebnis_json = models.JSONField(null=True, blank=True)
    fehler_meldung = models.TextField(blank=True)
    credits_verbraucht = models.IntegerField(default=1)
    importierter_pfad_pk = models.IntegerField(null=True, blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)
    fertig_am = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Formular-Analyse"
        verbose_name_plural = "Formular-Analysen"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.dateiname} [{self.status}]"


class CreditTransaktion(models.Model):
    """Buchungshistorie für Credits."""
    TYP_CHOICES = [
        ("kauf", "Kauf"),
        ("verbrauch", "Verbrauch"),
        ("rueckerstattung", "Rückerstattung"),
    ]
    account = models.ForeignKey(PortalAccount, on_delete=models.CASCADE, related_name="transaktionen")
    typ = models.CharField(max_length=20, choices=TYP_CHOICES)
    betrag = models.IntegerField()
    beschreibung = models.TextField(blank=True)
    stripe_payment_intent = models.CharField(max_length=100, blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Credit-Transaktion"
        verbose_name_plural = "Credit-Transaktionen"
        ordering = ["-erstellt_am"]

    def __str__(self):
        return f"{self.account.user.email}: {self.betrag:+d} ({self.typ})"


# ---------------------------------------------------------------------------
# Credit-Pakete (konfiguriert, nicht in DB)
# ---------------------------------------------------------------------------

CREDIT_PAKETE = [
    {
        "id": "starter",
        "name": "Starter",
        "credits": 5,
        "preis_cent": 990,
        "preis_str": "9,90 €",
        "beschreibung": "5 Formular-Analysen",
        "empfohlen": False,
    },
    {
        "id": "professional",
        "name": "Professional",
        "credits": 20,
        "preis_cent": 2990,
        "preis_str": "29,90 €",
        "beschreibung": "20 Formular-Analysen",
        "empfohlen": True,
    },
    {
        "id": "agentur",
        "name": "Agentur",
        "credits": 60,
        "preis_cent": 5990,
        "preis_str": "59,90 €",
        "beschreibung": "60 Formular-Analysen",
        "empfohlen": False,
    },
]

CREDIT_PAKETE_BY_ID = {p["id"]: p for p in CREDIT_PAKETE}
