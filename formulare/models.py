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
    benachrichtigung_email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Benachrichtigungs-E-Mail",
        help_text="Bei neuem Antrag wird eine formatierte E-Mail an diese Adresse gesendet, z.B. hundesteuer@gemeinde.de",
    )
    leika_schluessel = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="LeiKa-Schlüssel",
        help_text="14-stellige LeiKa-Leistungsnummer, z.B. 99108018026000 (Hundesteuer-Anmeldung)",
    )
    workflow_template = models.ForeignKey(
        "workflow.WorkflowTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verknuepfte_pfade",
        verbose_name="Workflow nach Abschluss",
        help_text="Dieser Workflow startet automatisch wenn der Antrag abgeschlossen wird.",
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
    tracking_token = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Tracking-Token",
        help_text="Token fuer oeffentliche Vorgangs-Verfolgung ohne Login",
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
        """Erzeugt eine eindeutige Vorgangsnummer im Format KUERZEL-LFDNR-DATUM-TOKEN."""
        import secrets as _secrets
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
        token = _secrets.token_hex(3).upper()  # 6-stelliger zufälliger Hex-Wert
        return f"{kuerzel}-{lfd:05d}-{jetzt.strftime('%Y%m%d')}-{token}"

    def abschliessen(self):
        """Markiert die Sitzung als abgeschlossen und generiert die Vorgangsnummer."""
        import secrets
        self.status = self.STATUS_ABGESCHLOSSEN
        self.abgeschlossen_am = timezone.now()
        if not self.vorgangsnummer:
            self.vorgangsnummer = AntrSitzung.generiere_vorgangsnummer(self.pfad)
        if not self.tracking_token:
            self.tracking_token = secrets.token_hex(32)
        self.save(update_fields=["status", "abgeschlossen_am", "vorgangsnummer", "tracking_token"])
        self._sende_tracking_email()
        self._sende_sachbearbeiter_email()
        self._trigger_webhook()

    def _trigger_webhook(self):
        try:
            from .webhook_service import trigger_antrag_eingereicht
            trigger_antrag_eingereicht(self)
        except Exception:
            pass

    def _sende_sachbearbeiter_email(self):
        """Sendet formatierte Eingangs-E-Mail ans konfigurierte Sachgebiets-Postfach."""
        empfaenger = self.pfad.benachrichtigung_email
        if not empfaenger:
            return
        try:
            from django.conf import settings as conf
            from django.core.mail import EmailMessage
            base_url = getattr(conf, "VORGANGSWERK_BASE_URL", "").rstrip("/")
            task_url = f"{base_url}/formulare/sitzung/{self.pk}/pdf/"
            vorgang_url = f"{base_url}/workflow/"

            # Felddaten aufbereiten
            felder_text = ""
            label_map = {}
            for schritt in self.pfad.schritte.all():
                for f in (schritt.felder_json or []):
                    if f.get("id") and f.get("label"):
                        label_map[f["id"]] = f["label"]
            for key, wert in (self.gesammelte_daten or {}).items():
                if key.startswith("__"):
                    continue
                label = label_map.get(key, key)
                if isinstance(wert, bool):
                    wert = "Ja" if wert else "Nein"
                felder_text += f"  {label:<30} {wert}\n"

            antragsteller = ""
            if self.user:
                antragsteller = self.user.get_full_name() or self.user.username
                if self.user.email:
                    antragsteller += f" <{self.user.email}>"
            elif self.email_anonym:
                antragsteller = self.email_anonym

            betreff = f"Neuer Antrag {self.vorgangsnummer} – {self.pfad.name}"
            text = (
                f"Neuer Antrag eingegangen\n"
                f"{'='*50}\n\n"
                f"Vorgangsnummer:  {self.vorgangsnummer}\n"
                f"Formular:        {self.pfad.name}\n"
                f"Eingereicht am:  {self.abgeschlossen_am.strftime('%d.%m.%Y um %H:%M')} Uhr\n"
                f"Antragsteller:   {antragsteller or '(anonym)'}\n\n"
                f"Angaben\n"
                f"{'-'*50}\n"
                f"{felder_text or '  (keine Angaben)'}\n"
                f"Links\n"
                f"{'-'*50}\n"
                f"  Arbeitsstapel:  {vorgang_url}\n"
                f"  Antrag als PDF: {task_url}\n"
            )
            if self.tracking_token:
                tracking_url = f"{base_url}/vorgang/{self.vorgangsnummer}/?token={self.tracking_token}"
                text += f"  Tracking-Link:  {tracking_url}\n"

            msg = EmailMessage(
                subject=betreff,
                body=text,
                to=[empfaenger],
            )
            # Hochgeladene Dateien anhängen
            for datei in self.dateien.all():
                msg.attach(datei.dateiname, bytes(datei.inhalt), datei.mime_type)
            msg.send(fail_silently=True)
        except Exception:
            pass

    def _sende_tracking_email(self):
        """Sendet Tracking-Link per E-Mail an den Antragsteller."""
        empfaenger = self.email_anonym
        if not empfaenger and self.user:
            empfaenger = self.user.email
        if not empfaenger:
            return
        try:
            from django.conf import settings as conf
            from django.core.mail import send_mail
            base_url = getattr(conf, "VORGANGSWERK_BASE_URL", "").rstrip("/")
            link = f"{base_url}/vorgang/{self.vorgangsnummer}/?token={self.tracking_token}"
            betreff = f"Ihr Antrag wurde eingereicht – {self.vorgangsnummer}"
            text = (
                f"Guten Tag,\n\n"
                f"Ihr Antrag \"{self.pfad.name}\" wurde erfolgreich eingereicht.\n\n"
                f"Vorgangsnummer: {self.vorgangsnummer}\n"
                f"Eingereicht am: {self.abgeschlossen_am.strftime('%d.%m.%Y %H:%M')} Uhr\n\n"
                f"Den aktuellen Bearbeitungsstand können Sie jederzeit hier einsehen:\n"
                f"{link}\n\n"
                f"Bitte bewahren Sie diesen Link sicher auf.\n\n"
                f"Mit freundlichen Grüßen\nIhr Vorgangswerk-Team"
            )
            send_mail(betreff, text, None, [empfaenger], fail_silently=True)
        except Exception:
            pass


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


class WebhookKonfiguration(models.Model):
    """Webhook-Endpunkt fuer die bezahlte Formularschnittstelle."""

    EREIGNIS_CHOICES = [
        ("antrag.eingereicht",     "Antrag eingereicht"),
        ("workflow.abgeschlossen", "Workflow abgeschlossen"),
        ("task.abgeschlossen",     "Task abgeschlossen"),
    ]

    name = models.CharField(max_length=200, verbose_name="Bezeichnung",
                            help_text="z.B. 'MACH-Anbindung Hundesteuer'")
    url = models.URLField(verbose_name="Ziel-URL",
                          help_text="HTTPS-Endpunkt der empfangenden Anwendung")
    secret = models.CharField(
        max_length=128,
        verbose_name="Signing-Secret",
        help_text="Wird für HMAC-SHA256-Signatur verwendet (X-Webhook-Signature)"
    )
    pfad = models.ForeignKey(
        AntrPfad,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="webhooks",
        verbose_name="Antragspfad",
        help_text="Leer = gilt für alle Pfade",
    )
    ereignisse = models.JSONField(
        default=list,
        verbose_name="Ereignisse",
        help_text="Liste der Ereignisse, z.B. ['antrag.eingereicht']",
    )
    aktiv = models.BooleanField(default=True, verbose_name="Aktiv")
    erstellt_am = models.DateTimeField(auto_now_add=True)
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="webhook_konfigurationen",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Webhook-Konfiguration"
        verbose_name_plural = "Webhook-Konfigurationen"

    def __str__(self):
        pfad_str = f" [{self.pfad.name}]" if self.pfad else " [global]"
        return f"{self.name}{pfad_str}"

    def ereignisse_display(self):
        labels = dict(self.EREIGNIS_CHOICES)
        return ", ".join(labels.get(e, e) for e in (self.ereignisse or []))


class WebhookZustellung(models.Model):
    """Protokoll jedes Zustellversuchs."""

    konfiguration = models.ForeignKey(
        WebhookKonfiguration,
        on_delete=models.CASCADE,
        related_name="zustellungen",
    )
    ereignis = models.CharField(max_length=50)
    payload_json = models.JSONField()
    versuche = models.IntegerField(default=0)
    letzter_status_code = models.IntegerField(null=True, blank=True)
    zugestellt_am = models.DateTimeField(null=True, blank=True)
    fehler = models.TextField(blank=True)
    erstellt_am = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Webhook-Zustellung"
        verbose_name_plural = "Webhook-Zustellungen"

    def __str__(self):
        status = "OK" if self.zugestellt_am else f"Fehler ({self.fehler[:40]})"
        return f"{self.ereignis} → {self.konfiguration.url[:40]} [{status}]"
