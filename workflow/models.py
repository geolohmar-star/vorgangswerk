# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Workflow-System Modelle

Dieses Modul definiert das Workflow-System bestehend aus:
- WorkflowTemplate: Wiederverwendbare Workflow-Definitionen (Blueprints)
- WorkflowStep: Einzelne Schritte innerhalb eines Templates
- WorkflowTransition: Uebergaenge zwischen Schritten (Graph-basiert)
- WorkflowInstance: Konkrete laufende Workflow-Instanzen
- WorkflowTask: Tasks im Arbeitsstapel der Bearbeiter
- WorkflowTrigger: Per GUI konfigurierbare Trigger-Definitionen
- ProzessAntrag: Antrag auf Erstellung eines neuen Prozesses
"""
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class WorkflowTemplate(models.Model):
    """Wiederverwendbare Workflow-Definition (Blueprint)."""

    KATEGORIE_GENEHMIGUNG = "genehmigung"
    KATEGORIE_PRUEFUNG = "pruefung"
    KATEGORIE_INFORMATION = "information"
    KATEGORIE_BEARBEITUNG = "bearbeitung"

    KATEGORIE_CHOICES = [
        (KATEGORIE_GENEHMIGUNG, "Genehmigung"),
        (KATEGORIE_PRUEFUNG, "Pruefung"),
        (KATEGORIE_INFORMATION, "Information"),
        (KATEGORIE_BEARBEITUNG, "Bearbeitung"),
    ]

    aktualisiert_am = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    beschreibung = models.TextField(blank=True, verbose_name="Beschreibung")
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    erstellt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erstellte_workflows",
        verbose_name="Erstellt von",
    )
    ist_aktiv = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Inaktive Templates koennen nicht gestartet werden",
    )
    ist_graph_workflow = models.BooleanField(
        default=True,
        verbose_name="Graph-basierter Workflow",
        help_text="Wenn True, werden Transitions verwendet statt Reihenfolge",
    )
    kategorie = models.CharField(
        max_length=50,
        choices=KATEGORIE_CHOICES,
        default=KATEGORIE_GENEHMIGUNG,
        verbose_name="Kategorie",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="Name",
        help_text="Name des Workflows (z.B. Urlaubsantrag-Genehmigung)",
    )
    trigger_event = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Trigger-Event",
        help_text="Event das diesen Workflow automatisch startet",
    )
    version = models.IntegerField(default=1, verbose_name="Version")

    class Meta:
        ordering = ["name"]
        verbose_name = "Workflow-Template"
        verbose_name_plural = "Workflow-Templates"

    def __str__(self):
        return f"{self.name} (v{self.version})"

    @property
    def anzahl_schritte(self):
        return self.schritte.count()

    @property
    def durchschnittliche_dauer(self):
        """Durchschnittliche Bearbeitungszeit aller abgeschlossenen Instanzen in Stunden."""
        abgeschlossene = self.instanzen.filter(status=WorkflowInstance.STATUS_ABGESCHLOSSEN)
        if not abgeschlossene.exists():
            return None
        dauern = []
        for instanz in abgeschlossene:
            if instanz.abgeschlossen_am:
                dauer = (instanz.abgeschlossen_am - instanz.gestartet_am).total_seconds() / 3600
                dauern.append(dauer)
        return sum(dauern) / len(dauern) if dauern else None


class WorkflowStep(models.Model):
    """Ein einzelner Schritt innerhalb eines Workflow-Templates."""

    AKTION_GENEHMIGEN = "genehmigen"
    AKTION_PRUEFEN = "pruefen"
    AKTION_INFORMIEREN = "informieren"
    AKTION_BEARBEITEN = "bearbeiten"
    AKTION_ENTSCHEIDEN = "entscheiden"
    AKTION_BENACHRICHTIGEN = "benachrichtigen"
    AKTION_EMAIL = "email"
    AKTION_WEBHOOK = "webhook"

    AKTION_CHOICES = [
        (AKTION_GENEHMIGEN, "Genehmigen"),
        (AKTION_PRUEFEN, "Pruefen"),
        (AKTION_INFORMIEREN, "Informieren"),
        (AKTION_BEARBEITEN, "Bearbeiten"),
        (AKTION_ENTSCHEIDEN, "Entscheiden"),
        (AKTION_BENACHRICHTIGEN, "Benachrichtigung senden"),
        (AKTION_EMAIL, "Email senden"),
        (AKTION_WEBHOOK, "Webhook aufrufen"),
    ]

    ROLLE_GRUPPE = "gruppe"
    ROLLE_SPEZIFISCHER_USER = "spezifischer_user"
    ROLLE_ANTRAGSTELLER = "antragsteller"

    ROLLE_CHOICES = [
        (ROLLE_GRUPPE, "Gruppe (alle Mitglieder sehen den Task)"),
        (ROLLE_SPEZIFISCHER_USER, "Spezifischer Benutzer"),
        (ROLLE_ANTRAGSTELLER, "Antragsteller selbst"),
    ]

    SCHRITT_TYP_CHOICES = [
        ("task", "Benutzer-Task (Standard)"),
        ("auto", "Automatische Aktion"),
        ("decision", "Entscheidungs-Node (mehrere Ausgaenge)"),
    ]

    # Konfiguration fuer automatische Aktionen (email, webhook etc.)
    auto_config = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Automatische Aktions-Konfiguration",
    )
    aktion_typ = models.CharField(
        max_length=50,
        choices=AKTION_CHOICES,
        default=AKTION_PRUEFEN,
        verbose_name="Aktionstyp",
    )
    beschreibung = models.TextField(
        blank=True,
        verbose_name="Beschreibung",
        help_text="Detaillierte Anweisungen fuer den Bearbeiter",
    )
    # Bedingungen fuer bedingte Aktivierung des Schritts
    bedingung_feld = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bedingungsfeld",
    )
    bedingung_operator = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            (">", "Groesser als"),
            ("<", "Kleiner als"),
            ("==", "Gleich"),
            ("!=", "Ungleich"),
            (">=", "Groesser oder gleich"),
            ("<=", "Kleiner oder gleich"),
        ],
        verbose_name="Bedingungsoperator",
    )
    bedingung_wert = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Bedingungswert",
    )
    eskalation_an_gruppe = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eskalations_schritte",
        verbose_name="Eskalation an Gruppe",
    )
    eskalation_nach_tagen = models.IntegerField(
        default=0,
        verbose_name="Eskalation nach (Tage)",
        help_text="0 = keine Eskalation",
    )
    frist_tage = models.IntegerField(
        default=3,
        verbose_name="Frist (Tage)",
    )
    ist_parallel = models.BooleanField(
        default=False,
        verbose_name="Parallel",
        help_text="Wird gleichzeitig mit naechstem Schritt ausgefuehrt",
    )
    # Position fuer Vis.js Graph-Editor
    node_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Node-ID",
        help_text="Eindeutige ID im Editor-Graph",
    )
    pos_x = models.FloatField(default=200, verbose_name="Position X")
    pos_y = models.FloatField(default=200, verbose_name="Position Y")
    reihenfolge = models.IntegerField(
        default=1,
        verbose_name="Reihenfolge",
        help_text="Fuer lineare Workflows – bei Graph-Workflows durch Transitions ersetzt",
    )
    schritt_typ = models.CharField(
        max_length=20,
        choices=SCHRITT_TYP_CHOICES,
        default="task",
        verbose_name="Schritt-Typ",
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="schritte",
        verbose_name="Template",
    )
    titel = models.CharField(max_length=200, verbose_name="Titel")
    # Zustaendigkeit: entweder Gruppe ODER spezifischer User
    zustaendig_gruppe = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_schritte",
        verbose_name="Zustaendige Gruppe",
        help_text="Alle Mitglieder der Gruppe sehen und koennen den Task bearbeiten",
    )
    zustaendig_rolle = models.CharField(
        max_length=50,
        choices=ROLLE_CHOICES,
        default=ROLLE_GRUPPE,
        verbose_name="Zustaendige Rolle",
    )
    zustaendig_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="zustaendige_workflow_schritte",
        verbose_name="Spezifischer Benutzer",
        help_text="Nur bei Rolle 'Spezifischer Benutzer'",
    )

    class Meta:
        ordering = ["template", "reihenfolge"]
        verbose_name = "Workflow-Schritt"
        verbose_name_plural = "Workflow-Schritte"

    def __str__(self):
        return f"{self.template.name} – {self.titel}"

    def bedingung_erfuellt(self, content_object):
        """Prueft ob die Bedingung fuer diesen Schritt erfuellt ist."""
        if not self.bedingung_feld:
            return True
        try:
            wert = getattr(content_object, self.bedingung_feld)
            bwert = float(self.bedingung_wert) if self.bedingung_wert else 0
            ops = {
                ">": wert > bwert, "<": wert < bwert,
                "==": wert == bwert, "!=": wert != bwert,
                ">=": wert >= bwert, "<=": wert <= bwert,
            }
            return ops.get(self.bedingung_operator, True)
        except (AttributeError, ValueError, TypeError):
            return True


class WorkflowTransition(models.Model):
    """Definiert Uebergaenge zwischen Workflow-Schritten (Graph-basiert)."""

    BEDINGUNG_CHOICES = [
        ("immer", "Immer (keine Bedingung)"),
        ("entscheidung", "Basierend auf Task-Entscheidung"),
        ("feld_wert", "Basierend auf Feld-Wert"),
    ]

    ENTSCHEIDUNG_CHOICES = [
        ("genehmigt", "Genehmigt"),
        ("abgelehnt", "Abgelehnt"),
        ("weitergeleitet", "Weitergeleitet"),
        ("rueckfrage", "Rueckfrage"),
        ("zurueck_antragsteller", "Zurueck an Antragsteller"),
    ]

    bedingung_entscheidung = models.CharField(
        max_length=30,
        choices=ENTSCHEIDUNG_CHOICES,
        null=True,
        blank=True,
        verbose_name="Erwartete Entscheidung",
    )
    bedingung_feld = models.CharField(max_length=100, blank=True, verbose_name="Bedingungsfeld")
    bedingung_operator = models.CharField(
        max_length=10,
        choices=[
            ("==", "Gleich"), ("!=", "Ungleich"),
            (">", "Groesser als"), ("<", "Kleiner als"),
            (">=", "Groesser oder gleich"), ("<=", "Kleiner oder gleich"),
            ("in", "Enthalten in"),
        ],
        blank=True,
        verbose_name="Operator",
    )
    bedingung_typ = models.CharField(
        max_length=20,
        choices=BEDINGUNG_CHOICES,
        default="immer",
        verbose_name="Bedingungstyp",
    )
    bedingung_wert = models.CharField(max_length=255, blank=True, verbose_name="Bedingungswert")
    label = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Beschriftung",
        help_text="z.B. 'genehmigt', 'abgelehnt'",
    )
    prioritaet = models.IntegerField(default=1, verbose_name="Prioritaet")
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="transitions",
        verbose_name="Template",
    )
    von_schritt = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="ausgaenge",
        verbose_name="Von Schritt",
    )
    zu_schritt = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="eingaenge",
        null=True,
        blank=True,
        verbose_name="Zu Schritt",
        help_text="NULL = Ende-Node",
    )

    class Meta:
        ordering = ["prioritaet"]
        verbose_name = "Workflow-Uebergang"
        verbose_name_plural = "Workflow-Uebergaenge"

    def __str__(self):
        zu = self.zu_schritt.titel if self.zu_schritt else "Ende"
        return f"{self.von_schritt.titel} -> {zu} ({self.get_bedingung_typ_display()})"

    def evaluate(self, task, content_object):
        """Evaluiert ob diese Transition greifen soll."""
        if self.bedingung_typ == "immer":
            return True
        elif self.bedingung_typ == "entscheidung":
            return task.entscheidung == self.bedingung_entscheidung
        elif self.bedingung_typ == "feld_wert":
            try:
                wert = getattr(content_object, self.bedingung_feld)
                return self._compare(wert, self.bedingung_operator, self.bedingung_wert)
            except AttributeError:
                return False
        return False

    def _compare(self, wert, operator, ziel_wert):
        try:
            if isinstance(wert, (int, float)):
                ziel_wert = float(ziel_wert)
        except (ValueError, TypeError):
            pass
        return {
            "==": wert == ziel_wert, "!=": wert != ziel_wert,
            ">": wert > ziel_wert, "<": wert < ziel_wert,
            ">=": wert >= ziel_wert, "<=": wert <= ziel_wert,
            "in": ziel_wert in str(wert),
        }.get(operator, False)


class WorkflowInstance(models.Model):
    """Eine konkrete laufende Instanz eines Workflows."""

    STATUS_LAUFEND = "laufend"
    STATUS_ABGESCHLOSSEN = "abgeschlossen"
    STATUS_ABGEBROCHEN = "abgebrochen"
    STATUS_PAUSIERT = "pausiert"

    STATUS_CHOICES = [
        (STATUS_LAUFEND, "Laufend"),
        (STATUS_ABGESCHLOSSEN, "Abgeschlossen"),
        (STATUS_ABGEBROCHEN, "Abgebrochen"),
        (STATUS_PAUSIERT, "Pausiert"),
    ]

    abgeschlossen_am = models.DateTimeField(null=True, blank=True, verbose_name="Abgeschlossen am")
    aktueller_schritt = models.ForeignKey(
        WorkflowStep,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aktive_instanzen",
        verbose_name="Aktueller Schritt",
    )
    # GenericForeignKey zum verknuepften Objekt (z.B. AntrSitzung)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")
    fortschritt = models.IntegerField(default=0, verbose_name="Fortschritt (%)")
    gestartet_am = models.DateTimeField(auto_now_add=True, verbose_name="Gestartet am")
    gestartet_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="gestartete_workflow_instanzen",
        verbose_name="Gestartet von",
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_LAUFEND,
        verbose_name="Status",
    )
    template = models.ForeignKey(
        WorkflowTemplate,
        on_delete=models.PROTECT,
        related_name="instanzen",
        verbose_name="Template",
    )

    class Meta:
        ordering = ["-gestartet_am"]
        verbose_name = "Workflow-Instanz"
        verbose_name_plural = "Workflow-Instanzen"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["status", "gestartet_am"]),
        ]

    def __str__(self):
        return f"{self.template.name} #{self.id} ({self.get_status_display()})"

    @property
    def ist_laufend(self):
        return self.status == self.STATUS_LAUFEND

    @property
    def ist_abgeschlossen(self):
        return self.status == self.STATUS_ABGESCHLOSSEN

    @property
    def dauer_stunden(self):
        ende = self.abgeschlossen_am or timezone.now()
        return (ende - self.gestartet_am).total_seconds() / 3600

    def berechne_fortschritt(self):
        alle = self.tasks.count()
        if alle == 0:
            return 0
        erledigt = self.tasks.filter(status=WorkflowTask.STATUS_ERLEDIGT).count()
        return int((erledigt / alle) * 100)

    def update_fortschritt(self):
        self.fortschritt = self.berechne_fortschritt()
        self.save(update_fields=["fortschritt"])


class WorkflowTask(models.Model):
    """Ein Task im Arbeitsstapel eines Bearbeiters."""

    STATUS_OFFEN = "offen"
    STATUS_IN_BEARBEITUNG = "in_bearbeitung"
    STATUS_ERLEDIGT = "erledigt"
    STATUS_UEBERSPRUNGEN = "uebersprungen"
    STATUS_ESKALIERT = "eskaliert"

    STATUS_CHOICES = [
        (STATUS_OFFEN, "Offen"),
        (STATUS_IN_BEARBEITUNG, "In Bearbeitung"),
        (STATUS_ERLEDIGT, "Erledigt"),
        (STATUS_UEBERSPRUNGEN, "Uebersprungen"),
        (STATUS_ESKALIERT, "Eskaliert"),
    ]

    ENTSCHEIDUNG_GENEHMIGT = "genehmigt"
    ENTSCHEIDUNG_ABGELEHNT = "abgelehnt"
    ENTSCHEIDUNG_WEITERGELEITET = "weitergeleitet"
    ENTSCHEIDUNG_RUECKFRAGE = "rueckfrage"
    ENTSCHEIDUNG_ZURUECK_ANTRAGSTELLER = "zurueck_antragsteller"

    ENTSCHEIDUNG_CHOICES = [
        (ENTSCHEIDUNG_GENEHMIGT, "Genehmigt"),
        (ENTSCHEIDUNG_ABGELEHNT, "Abgelehnt"),
        (ENTSCHEIDUNG_WEITERGELEITET, "Weitergeleitet"),
        (ENTSCHEIDUNG_RUECKFRAGE, "Rueckfrage"),
        (ENTSCHEIDUNG_ZURUECK_ANTRAGSTELLER, "Zurueck an Antragsteller"),
    ]

    # Claim-Felder fuer Gruppen-Tasks
    claimed_am = models.DateTimeField(null=True, blank=True, verbose_name="Geclaimed am")
    claimed_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="claimed_workflow_tasks",
        verbose_name="Geclaimed von",
    )
    entscheidung = models.CharField(
        max_length=50,
        choices=ENTSCHEIDUNG_CHOICES,
        blank=True,
        verbose_name="Entscheidung",
    )
    erledigt_am = models.DateTimeField(null=True, blank=True, verbose_name="Erledigt am")
    erledigt_von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="erledigte_workflow_tasks",
        verbose_name="Erledigt von",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    frist = models.DateTimeField(verbose_name="Frist")
    gestartet_am = models.DateTimeField(null=True, blank=True, verbose_name="Gestartet am")
    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Workflow-Instanz",
    )
    kommentar = models.TextField(blank=True, verbose_name="Kommentar")
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default=STATUS_OFFEN,
        verbose_name="Status",
    )
    step = models.ForeignKey(
        WorkflowStep,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Workflow-Schritt",
    )
    # Zustaendigkeit: Gruppe ODER spezifischer User
    zugewiesen_an_gruppe = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_tasks",
        verbose_name="Zugewiesen an Gruppe",
    )
    zugewiesen_an_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_tasks",
        verbose_name="Zugewiesen an Benutzer",
    )

    class Meta:
        ordering = ["frist", "-erstellt_am"]
        verbose_name = "Workflow-Task"
        verbose_name_plural = "Workflow-Tasks"
        indexes = [
            models.Index(fields=["status", "frist"]),
            models.Index(fields=["zugewiesen_an_gruppe", "status"]),
        ]

    def __str__(self):
        return f"Task #{self.id}: {self.step.titel} ({self.get_status_display()})"

    @property
    def ist_ueberfaellig(self):
        if self.status in [self.STATUS_ERLEDIGT, self.STATUS_UEBERSPRUNGEN]:
            return False
        return timezone.now() > self.frist

    @property
    def ist_heute_faellig(self):
        if self.status in [self.STATUS_ERLEDIGT, self.STATUS_UEBERSPRUNGEN]:
            return False
        return self.frist.date() == timezone.now().date()

    @property
    def tage_bis_frist(self):
        if self.status in [self.STATUS_ERLEDIGT, self.STATUS_UEBERSPRUNGEN]:
            return None
        return (self.frist - timezone.now()).days

    def kann_bearbeiten(self, user):
        """Prueft ob der User diesen Task bearbeiten darf."""
        if self.status not in [self.STATUS_OFFEN, self.STATUS_IN_BEARBEITUNG]:
            return False
        if self.zugewiesen_an_user:
            return user == self.zugewiesen_an_user
        if self.zugewiesen_an_gruppe:
            return self.zugewiesen_an_gruppe.user_set.filter(pk=user.pk).exists()
        # Staff darf alles
        return user.is_staff


class ProzessAntrag(models.Model):
    """Antrag auf Erstellung eines neuen Workflow-Prozesses."""

    AUSLOESER_MANUELL = "manuell"
    AUSLOESER_FORMULAR = "formular"
    AUSLOESER_ZEITGESTEUERT = "zeitgesteuert"
    AUSLOESER_SONSTIGES = "sonstiges"

    AUSLOESER_CHOICES = [
        (AUSLOESER_MANUELL, "Manuell (Benutzer startet selbst)"),
        (AUSLOESER_FORMULAR, "Formular-Einreichung"),
        (AUSLOESER_ZEITGESTEUERT, "Zeitgesteuert"),
        (AUSLOESER_SONSTIGES, "Sonstiges"),
    ]

    STATUS_EINGEREICHT = "eingereicht"
    STATUS_IN_PRUEFUNG = "in_pruefung"
    STATUS_IN_UMSETZUNG = "in_umsetzung"
    STATUS_UMGESETZT = "umgesetzt"
    STATUS_ABGELEHNT = "abgelehnt"

    STATUS_CHOICES = [
        (STATUS_EINGEREICHT, "Eingereicht"),
        (STATUS_IN_PRUEFUNG, "In Pruefung"),
        (STATUS_IN_UMSETZUNG, "In Umsetzung"),
        (STATUS_UMGESETZT, "Umgesetzt"),
        (STATUS_ABGELEHNT, "Abgelehnt"),
    ]

    aktualisiert_am = models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")
    antragsteller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="prozessantraege",
        verbose_name="Antragsteller",
    )
    ausloeser_detail = models.TextField(blank=True, verbose_name="Genauere Beschreibung des Ausloesers")
    ausloeser_typ = models.CharField(
        max_length=20,
        choices=AUSLOESER_CHOICES,
        default=AUSLOESER_MANUELL,
        verbose_name="Wie wird der Prozess ausgeloest?",
    )
    bemerkungen = models.TextField(blank=True, verbose_name="Zusaetzliche Bemerkungen")
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Eingereicht am")
    name = models.CharField(max_length=200, verbose_name="Name des Prozesses")
    pdf_benoetigt = models.BooleanField(default=False, verbose_name="Soll am Ende ein PDF erzeugt werden?")
    schritte = models.JSONField(default=list, verbose_name="Prozessschritte")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_EINGEREICHT,
        verbose_name="Status",
    )
    team_benoetigt = models.BooleanField(default=False, verbose_name="Wird ein Team benoetigt?")
    team_vorschlag = models.TextField(blank=True, verbose_name="Team-Vorschlag")
    workflow_instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prozessantraege",
        verbose_name="Workflow-Instanz",
    )
    ziel = models.TextField(verbose_name="Ziel des Prozesses")

    class Meta:
        ordering = ["-erstellt_am"]
        verbose_name = "Prozessantrag"
        verbose_name_plural = "Prozessantraege"

    def __str__(self):
        name = self.antragsteller.get_full_name() or self.antragsteller.username
        return f"Prozessantrag: {self.name} ({name})"


class WorkflowTrigger(models.Model):
    """Per GUI konfigurierbarer Trigger fuer automatischen Workflow-Start."""

    TRIGGER_AUF_ERSTELLT = "erstellt"
    TRIGGER_AUF_AKTUALISIERT = "aktualisiert"

    TRIGGER_AUF_CHOICES = [
        (TRIGGER_AUF_ERSTELLT, "Neu erstellt"),
        (TRIGGER_AUF_AKTUALISIERT, "Aktualisiert"),
    ]

    antragsteller_pfad = models.CharField(
        max_length=200,
        default="erstellt_von",
        verbose_name="Antragsteller-Pfad",
        help_text="Punkt-getrennter Attributpfad zum User-Objekt (z.B. 'erstellt_von' oder 'user')",
    )
    beschreibung = models.TextField(blank=True, verbose_name="Beschreibung")
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Django-Model",
    )
    erstellt_am = models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")
    ist_aktiv = models.BooleanField(default=True, verbose_name="Aktiv")
    name = models.CharField(max_length=200, verbose_name="Name")
    trigger_auf = models.CharField(
        max_length=20,
        choices=TRIGGER_AUF_CHOICES,
        default=TRIGGER_AUF_ERSTELLT,
        verbose_name="Ausloesen bei",
    )
    trigger_event = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Trigger-Event-Key",
        help_text="Eindeutiger Schluessel (muss mit WorkflowTemplate.trigger_event uebereinstimmen)",
    )
    workflow_instance_feld = models.CharField(
        max_length=100,
        default="workflow_instance",
        verbose_name="Workflow-Instance-Feld",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Workflow-Trigger"
        verbose_name_plural = "Workflow-Trigger"

    def __str__(self):
        status = "aktiv" if self.ist_aktiv else "inaktiv"
        model_name = self.content_type.model if self.content_type else "kein Model"
        return f"{self.name} [{model_name} -> {self.trigger_event}] ({status})"

    def get_user_from_instance(self, instance):
        """Folgt dem antragsteller_pfad und gibt den User zurueck."""
        obj = instance
        for teil in self.antragsteller_pfad.split("."):
            obj = getattr(obj, teil, None)
            if obj is None:
                return None
        return obj
