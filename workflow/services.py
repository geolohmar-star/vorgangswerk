# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Workflow-Engine: Zentrale Logik fuer Workflow-Verwaltung."""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import WorkflowInstance, WorkflowStep, WorkflowTask, WorkflowTransition

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Zentrale Workflow-Engine ohne externe App-Abhaengigkeiten."""

    def start_workflow(self, template, content_object, user):
        """Startet einen neuen Workflow aus einem Template.

        Args:
            template: WorkflowTemplate Instanz
            content_object: Verknuepftes Objekt (z.B. AntrSitzung)
            user: User der den Workflow startet

        Returns:
            WorkflowInstance
        """
        from django.contrib.contenttypes.models import ContentType

        with transaction.atomic():
            content_type = ContentType.objects.get_for_model(content_object)
            instance = WorkflowInstance.objects.create(
                template=template,
                content_type=content_type,
                object_id=content_object.pk,
                status=WorkflowInstance.STATUS_LAUFEND,
                gestartet_von=user,
                fortschritt=0,
            )

            if template.ist_graph_workflow:
                # Graph-Workflow: erste Schritte ohne eingehende Transitions
                start_schritte = self._finde_start_schritte(template)
            else:
                # Linearer Workflow: Schritte mit reihenfolge=1
                start_schritte = list(template.schritte.filter(reihenfolge=1))

            for schritt in start_schritte:
                self.create_tasks_for_step(instance, schritt, content_object)

            if start_schritte:
                instance.aktueller_schritt = start_schritte[0]
                instance.save(update_fields=["aktueller_schritt"])

            instance.update_fortschritt()
            return instance

    def _finde_start_schritte(self, template):
        """Findet Schritte ohne eingehende Transitions (Start-Nodes)."""
        alle = set(template.schritte.values_list("pk", flat=True))
        mit_eingang = set(
            template.transitions.exclude(zu_schritt__isnull=True)
            .values_list("zu_schritt_id", flat=True)
        )
        start_ids = alle - mit_eingang
        return list(template.schritte.filter(pk__in=start_ids).order_by("reihenfolge"))

    def create_tasks_for_step(self, instance, step, content_object=None):
        """Erstellt Tasks fuer einen WorkflowStep.

        Bei Schritt-Typ 'auto' wird die Aktion sofort ausgefuehrt.
        Bei Schritt-Typ 'task' wird ein WorkflowTask-Objekt erstellt.
        """
        if not step.bedingung_erfuellt(content_object) if content_object else False:
            return []

        if step.schritt_typ == "auto":
            self._execute_auto_action(step, instance, content_object)
            # Sofort naechste Schritte aktivieren
            fake_task = _FakeTask(step=step, instance=instance, entscheidung="auto_completed")
            if instance.template.ist_graph_workflow:
                for next_step in self.get_next_steps_via_transitions(fake_task, content_object):
                    self.create_tasks_for_step(instance, next_step, content_object)
            return []

        frist = timezone.now() + timedelta(days=step.frist_tage)

        # Zustaendigkeit ermitteln
        gruppe = None
        user = None
        if step.zustaendig_rolle == WorkflowStep.ROLLE_GRUPPE:
            gruppe = step.zustaendig_gruppe
        elif step.zustaendig_rolle == WorkflowStep.ROLLE_SPEZIFISCHER_USER:
            user = step.zustaendig_user
        elif step.zustaendig_rolle == WorkflowStep.ROLLE_ANTRAGSTELLER:
            # Antragsteller aus content_object ermitteln
            user = self._get_antragsteller(content_object)

        task = WorkflowTask.objects.create(
            instance=instance,
            step=step,
            zugewiesen_an_gruppe=gruppe,
            zugewiesen_an_user=user,
            status=WorkflowTask.STATUS_OFFEN,
            frist=frist,
        )
        return [task]

    def _get_antragsteller(self, content_object):
        """Versucht den Antragsteller aus dem verknuepften Objekt zu ermitteln."""
        if content_object is None:
            return None
        for attr in ("user", "antragsteller", "erstellt_von", "gestartet_von"):
            val = getattr(content_object, attr, None)
            if val is not None:
                return val
        return None

    def complete_task(self, task, user, entscheidung="genehmigt", kommentar=""):
        """Schliesst einen Task ab und aktiviert naechste Schritte.

        Args:
            task: WorkflowTask der abgeschlossen wird
            user: User der den Task abschliesst
            entscheidung: Entscheidungs-String (genehmigt, abgelehnt, ...)
            kommentar: Optionaler Kommentar

        Returns:
            WorkflowInstance (aktualisiert)
        """
        with transaction.atomic():
            task.status = WorkflowTask.STATUS_ERLEDIGT
            task.entscheidung = entscheidung
            task.kommentar = kommentar
            task.erledigt_am = timezone.now()
            task.erledigt_von = user
            task.save()

            instance = task.instance
            content_object = instance.content_object

            if instance.template.ist_graph_workflow:
                naechste = self.get_next_steps_via_transitions(task, content_object)
            else:
                naechste = self._naechste_lineare_schritte(task)

            if naechste:
                for schritt in naechste:
                    self.create_tasks_for_step(instance, schritt, content_object)
                instance.aktueller_schritt = naechste[0]
                instance.save(update_fields=["aktueller_schritt"])
            else:
                # Kein weiterer Schritt – Workflow abschliessen
                offene = instance.tasks.filter(
                    status__in=[WorkflowTask.STATUS_OFFEN, WorkflowTask.STATUS_IN_BEARBEITUNG]
                ).exclude(pk=task.pk)
                if not offene.exists():
                    instance.status = WorkflowInstance.STATUS_ABGESCHLOSSEN
                    instance.abgeschlossen_am = timezone.now()
                    instance.save(update_fields=["status", "abgeschlossen_am"])

            instance.update_fortschritt()
            return instance

    def get_next_steps_via_transitions(self, task, content_object):
        """Findet naechste Schritte basierend auf Transitions (Graph-Logik)."""
        transitions = WorkflowTransition.objects.filter(
            von_schritt=task.step
        ).order_by("prioritaet")

        naechste = []
        for transition in transitions:
            if transition.evaluate(task, content_object):
                if transition.zu_schritt is not None:
                    naechste.append(transition.zu_schritt)
                # zu_schritt=None bedeutet Ende-Node – kein weiterer Schritt
        return naechste

    def _naechste_lineare_schritte(self, task):
        """Findet den naechsten Schritt bei linearem Workflow."""
        aktuelle_reihenfolge = task.step.reihenfolge
        return list(
            task.instance.template.schritte.filter(
                reihenfolge=aktuelle_reihenfolge + 1
            )
        )

    def _execute_auto_action(self, step, instance, content_object):
        """Fuehrt eine automatische Aktion aus (Email, Webhook)."""
        config = step.auto_config or {}
        aktion = step.aktion_typ

        if aktion == WorkflowStep.AKTION_EMAIL:
            self._send_email(config, instance, content_object)
        elif aktion == WorkflowStep.AKTION_WEBHOOK:
            self._call_webhook(config, instance, content_object)
        elif aktion == WorkflowStep.AKTION_BENACHRICHTIGEN:
            logger.info("Benachrichtigung: %s – %s", instance, config.get("nachricht", ""))

    def _send_email(self, config, instance, content_object):
        """Sendet eine automatische E-Mail."""
        from django.core.mail import send_mail
        betreff = config.get("betreff", f"Workflow: {instance.template.name}")
        text = config.get("text", "")
        empfaenger = config.get("empfaenger", "")
        if not empfaenger:
            return
        try:
            send_mail(betreff, text, None, [empfaenger], fail_silently=True)
        except Exception as exc:
            logger.error("Workflow-Email fehlgeschlagen: %s", exc)

    def _call_webhook(self, config, instance, content_object):
        """Ruft einen Webhook auf."""
        import json
        try:
            import urllib.request
            url = config.get("url", "")
            if not url:
                return
            data = json.dumps(config.get("data", {})).encode()
            req = urllib.request.Request(url, data=data, method=config.get("method", "POST"))
            req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            logger.error("Webhook fehlgeschlagen: %s", exc)


class _FakeTask:
    """Hilfsobjekt fuer automatische Schritte ohne echten Task."""

    def __init__(self, step, instance, entscheidung):
        self.step = step
        self.instance = instance
        self.entscheidung = entscheidung
