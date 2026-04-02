# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""core – Models: Benutzerprofil, Audit-Log."""
import logging

from django.contrib.auth.models import User
from django.db import models

logger = logging.getLogger("vorgangswerk")


# ---------------------------------------------------------------------------
# Benutzerprofil
# ---------------------------------------------------------------------------

class Benutzerprofil(models.Model):
    """Erweiterung des Django-Users um Vorgangswerk-spezifische Felder.

    Rollen werden ueber Django-Gruppen abgebildet:
      - Administratoren  (Gruppe: "Administratoren")
      - Bearbeiter       (Gruppe: "Bearbeiter")
      - Antragsteller    (alle authentifizierten User ohne Gruppe)
    """

    SPRACHE_CHOICES = [
        ("de", "Deutsch"),
        ("en", "Englisch"),
    ]

    abteilung = models.CharField(
        max_length=200, blank=True, verbose_name="Abteilung"
    )
    sprache = models.CharField(
        max_length=5,
        choices=SPRACHE_CHOICES,
        default="de",
        verbose_name="Sprache",
    )
    telefon = models.CharField(
        max_length=50, blank=True, verbose_name="Telefon"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profil",
        verbose_name="Benutzer",
    )

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        verbose_name = "Benutzerprofil"
        verbose_name_plural = "Benutzerprofile"

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def ist_administrator(self):
        """Prueft ob der User in der Gruppe 'Administratoren' ist."""
        return self.user.groups.filter(name="Administratoren").exists()

    def ist_bearbeiter(self):
        """Prueft ob der User in der Gruppe 'Bearbeiter' ist."""
        return self.user.groups.filter(name="Bearbeiter").exists()


# ---------------------------------------------------------------------------
# Audit-Log (BSI: alle sicherheitsrelevanten Aktionen protokollieren)
# ---------------------------------------------------------------------------

class AuditLog(models.Model):
    """Unveraenderlicher Audit-Trail fuer alle sicherheitsrelevanten Aktionen.

    BSI IT-Grundschutz ORP.4 / APP.3.1 – Rechenschaftspflicht.
    Kein delete(), kein update() ueber normalen Manager.
    """

    AKTION_CHOICES = [
        ("login", "Anmeldung"),
        ("logout", "Abmeldung"),
        ("login_fehlgeschlagen", "Anmeldung fehlgeschlagen"),
        ("erstellt", "Objekt erstellt"),
        ("geaendert", "Objekt geaendert"),
        ("geloescht", "Objekt geloescht"),
        ("zugriff", "Zugriff"),
        ("export", "Export"),
        ("import", "Import"),
        ("passwort_geaendert", "Passwort geaendert"),
    ]

    aktion = models.CharField(
        max_length=30,
        choices=AKTION_CHOICES,
        verbose_name="Aktion",
    )
    app = models.CharField(
        max_length=50, blank=True, verbose_name="App"
    )
    beschreibung = models.TextField(
        blank=True, verbose_name="Beschreibung"
    )
    ip_adresse = models.GenericIPAddressField(
        null=True, blank=True, verbose_name="IP-Adresse"
    )
    objekt_id = models.CharField(
        max_length=50, blank=True, verbose_name="Objekt-ID"
    )
    objekt_typ = models.CharField(
        max_length=100, blank=True, verbose_name="Objekt-Typ"
    )
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="Benutzer",
    )
    zeitpunkt = models.DateTimeField(
        auto_now_add=True, verbose_name="Zeitpunkt"
    )

    class Meta:
        ordering = ["-zeitpunkt"]
        verbose_name = "Audit-Log"
        verbose_name_plural = "Audit-Logs"

    def __str__(self):
        username = self.user.username if self.user else "anonym"
        return f"{username} – {self.aktion} – {self.zeitpunkt:%d.%m.%Y %H:%M}"


# ---------------------------------------------------------------------------
# Hilfsfunktion: Audit-Eintrag schreiben
# ---------------------------------------------------------------------------

def audit(request, aktion, beschreibung="", app="", objekt_id="", objekt_typ=""):
    """Schreibt einen Audit-Log-Eintrag. Nie sensible Daten uebergeben."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    if not ip:
        ip = request.META.get("REMOTE_ADDR")
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        aktion=aktion,
        beschreibung=beschreibung,
        app=app,
        objekt_id=str(objekt_id),
        objekt_typ=objekt_typ,
        ip_adresse=ip or None,
    )
