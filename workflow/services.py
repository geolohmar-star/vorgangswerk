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
            verteiler_task = None
            if step.aktion_typ == WorkflowStep.AKTION_VERTEILEN:
                # Verteiler-Schritt: Task anlegen damit VerteilEmpfaenger daran haengen
                verteiler_task = WorkflowTask.objects.create(
                    instance=instance,
                    step=step,
                    status=WorkflowTask.STATUS_ERLEDIGT,
                    erledigt_am=timezone.now(),
                    frist=timezone.now(),
                )
            self._execute_auto_action(step, instance, content_object, task=verteiler_task)
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
        self._benachrichtige_neue_aufgabe(task)
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
            self._trigger_webhook_task(task)

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
                    self._benachrichtige_abschluss(instance)
                    self._trigger_webhook_abschluss(instance)

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

    def _execute_auto_action(self, step, instance, content_object, task=None):
        """Fuehrt eine automatische Aktion aus (Email, Webhook)."""
        config = step.auto_config or {}
        aktion = step.aktion_typ

        if aktion == WorkflowStep.AKTION_EMAIL:
            self._send_email(config, instance, content_object)
        elif aktion == WorkflowStep.AKTION_WEBHOOK:
            self._call_webhook(config, instance, content_object)
        elif aktion == WorkflowStep.AKTION_BENACHRICHTIGEN:
            logger.info("Benachrichtigung: %s – %s", instance, config.get("nachricht", ""))
        elif aktion == WorkflowStep.AKTION_VERTEILEN:
            self._verteile_akte(config, instance, content_object, task=task)

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

    def _verteile_akte(self, config, instance, content_object, task=None):
        """
        Verteiler/Postbote: Versendet Kopien der Akte per E-Mail mit Bestaetigunslink.

        auto_config-Felder:
          empfaenger      – kommagetrennte E-Mail-Adressen (Format: "Name <email>" oder nur email)
          empfaenger_namen– kommagetrennte Bezeichnungen passend zu empfaenger (optional)
          dokumente       – "alle" | "antrag_pdf" | "auswahl"
          ausgewaehlte    – Liste von Dokument-IDs (bei "auswahl")
          begleittext     – optionaler Begleittext
          betreff         – optionaler Betreff
        """
        from django.core.mail import EmailMessage
        from django.conf import settings
        from django.utils import timezone as tz

        empfaenger_raw = config.get("empfaenger", "")
        empfaenger_namen_raw = config.get("empfaenger_namen", "")
        empfaenger_liste = [e.strip() for e in empfaenger_raw.split(",") if e.strip()]
        namen_liste = [n.strip() for n in empfaenger_namen_raw.split(",") if n.strip()]

        if not empfaenger_liste:
            logger.warning("Verteiler-Schritt: Keine Empfänger konfiguriert.")
            return

        dokumente_typ = config.get("dokumente", "antrag_pdf")
        begleittext   = config.get("begleittext", "")
        betreff       = config.get("betreff", "") or f"Akte: {instance.template.name}"
        base_url      = getattr(settings, "VORGANGSWERK_BASE_URL", "http://localhost:8100")

        anhaenge = []

        # Antrags-PDF generieren
        if dokumente_typ in ("alle", "antrag_pdf"):
            try:
                pdf_bytes = self._generiere_antrags_pdf(content_object)
                if pdf_bytes:
                    anhaenge.append(("antrag.pdf", pdf_bytes, "application/pdf"))
            except Exception as e:
                logger.warning("Verteiler: Antrags-PDF konnte nicht generiert werden: %s", e)

        # Ausgewaehlte Dokumente aus DMS
        if dokumente_typ in ("alle", "auswahl"):
            try:
                from dokumente.models import Dokument
                ausgewaehlte_ids = config.get("ausgewaehlte", [])
                docs = (
                    Dokument.objects.filter(vorgangs_referenz=str(instance.pk))
                    if dokumente_typ == "alle"
                    else Dokument.objects.filter(pk__in=ausgewaehlte_ids)
                )
                for dok in docs:
                    try:
                        inhalt = dok.datei_inhalt
                        if inhalt:
                            anhaenge.append((dok.dateiname, bytes(inhalt), "application/octet-stream"))
                    except Exception:
                        pass
            except Exception as e:
                logger.warning("Verteiler: Dokumente konnten nicht geladen werden: %s", e)

        # Pro Empfaenger: VerteilEmpfaenger anlegen + Mail mit Bestaetigunslink senden
        for i, adresse in enumerate(empfaenger_liste):
            name = namen_liste[i] if i < len(namen_liste) else adresse
            ve = None

            # VerteilEmpfaenger-Eintrag anlegen (nur wenn task bekannt)
            if task:
                try:
                    from post.models import VerteilEmpfaenger
                    ve = VerteilEmpfaenger.objects.create(
                        workflow_task=task,
                        name=name,
                        email=adresse,
                        typ=VerteilEmpfaenger.TYP_EMAIL,
                        status=VerteilEmpfaenger.STATUS_AUSSTEHEND,
                    )
                except Exception as pe:
                    logger.warning("VerteilEmpfaenger anlegen fehlgeschlagen: %s", pe)

            try:
                bestaetigung_url = (
                    f"{base_url}/postbuch/bestaetigung/{ve.token}/"
                    if ve else ""
                )
                body = (
                    f"{begleittext}\n\n" if begleittext else
                    f"Anbei erhalten Sie die Unterlagen zum Vorgang '{instance.template.name}'.\n\n"
                )
                if bestaetigung_url:
                    body += (
                        f"Bitte bestaetigen Sie den Erhalt durch Klick auf folgenden Link:\n"
                        f"{bestaetigung_url}\n\n"
                    )
                body += "Vorgangswerk"

                mail = EmailMessage(
                    subject=betreff,
                    body=body,
                    to=[adresse],
                )
                for dateiname, inhalt, mime in anhaenge:
                    mail.attach(dateiname, inhalt, mime)
                mail.send(fail_silently=False)
                logger.info("Verteiler: Akte an %s versendet (%d Anhänge)", adresse, len(anhaenge))

                if ve:
                    ve.status = VerteilEmpfaenger.STATUS_VERSENDET
                    ve.versendet_am = tz.now()
                    ve.save(update_fields=["status", "versendet_am"])

                # Postbuch-Eintrag (Ausgang)
                try:
                    from post.models import Posteintrag
                    Posteintrag.objects.create(
                        datum=tz.now().date(),
                        richtung=Posteintrag.RICHTUNG_AUSGANG,
                        typ=Posteintrag.TYP_EMAIL,
                        absender_empfaenger=f"{name} <{adresse}>",
                        betreff=betreff,
                        vorgang_bezug=str(instance.pk),
                    )
                except Exception as pe:
                    logger.warning("Postbuch-Eintrag fehlgeschlagen: %s", pe)

            except Exception as e:
                logger.error("Verteiler: Versand an %s fehlgeschlagen: %s", adresse, e)
                if ve:
                    ve.notiz = f"Versand fehlgeschlagen: {e}"
                    ve.save(update_fields=["notiz"])

    def _generiere_antrags_pdf(self, content_object):
        """Versucht ein Antrags-PDF aus dem verknüpften Objekt zu generieren."""
        try:
            from formulare.models import AntrSitzung
            from formulare.views import _generiere_pdf_bytes
            if isinstance(content_object, AntrSitzung):
                return _generiere_pdf_bytes(content_object)
        except Exception as e:
            logger.debug("Antrags-PDF nicht generierbar: %s", e)
        return None

    def _benachrichtige_neue_aufgabe(self, task):
        """Sendet E-Mail-Benachrichtigung bei neuer Aufgabe."""
        empfaenger = self._task_empfaenger(task)
        for user in empfaenger:
            try:
                profil = user.profil
                if not profil.email_bei_neuer_aufgabe:
                    continue
            except Exception:
                pass  # kein Profil = Standard = senden
            if not user.email:
                continue
            self._sende_aufgaben_email(user, task)

    def _benachrichtige_abschluss(self, instance):
        """Sendet E-Mail-Benachrichtigung bei Workflow-Abschluss."""
        antragsteller = self._get_antragsteller(instance.content_object)
        if not antragsteller or not antragsteller.email:
            return
        try:
            profil = antragsteller.profil
            if not profil.email_bei_abschluss:
                return
        except Exception:
            pass
        from django.conf import settings
        from django.core.mail import send_mail
        base_url = getattr(settings, "VORGANGSWERK_BASE_URL", "").rstrip("/")
        betreff = f"[Vorgangswerk] Ihr Vorgang wurde abgeschlossen"
        content_object = instance.content_object
        vgnr = getattr(content_object, "vorgangsnummer", "") or f"#{instance.pk}"
        text = (
            f"Guten Tag {antragsteller.get_full_name() or antragsteller.username},\n\n"
            f"Ihr Vorgang {vgnr} wurde abgeschlossen.\n\n"
            f"Mit freundlichen Grüßen\nIhr Vorgangswerk-Team"
        )
        try:
            send_mail(betreff, text, None, [antragsteller.email], fail_silently=True)
        except Exception as exc:
            logger.error("Abschluss-Benachrichtigung fehlgeschlagen: %s", exc)

    def _trigger_webhook_task(self, task):
        try:
            from formulare.webhook_service import trigger_task_abgeschlossen
            trigger_task_abgeschlossen(task)
        except Exception:
            logger.exception("Webhook task.abgeschlossen fehlgeschlagen")

    def _trigger_webhook_abschluss(self, instance):
        try:
            from formulare.webhook_service import trigger_workflow_abgeschlossen
            trigger_workflow_abgeschlossen(instance)
        except Exception:
            logger.exception("Webhook workflow.abgeschlossen fehlgeschlagen")

    def _task_empfaenger(self, task):
        """Gibt Liste der zu benachrichtigenden User für einen Task zurück."""
        empfaenger = []
        if task.zugewiesen_an_user:
            empfaenger.append(task.zugewiesen_an_user)
        elif task.zugewiesen_an_gruppe:
            empfaenger = list(task.zugewiesen_an_gruppe.user_set.filter(is_active=True))
        return empfaenger

    def _sende_aufgaben_email(self, user, task):
        """Sendet die eigentliche Aufgaben-E-Mail."""
        from django.conf import settings
        from django.core.mail import send_mail
        base_url = getattr(settings, "VORGANGSWERK_BASE_URL", "").rstrip("/")
        instance = task.instance
        content_object = instance.content_object
        vgnr = getattr(content_object, "vorgangsnummer", "") or f"Instanz #{instance.pk}"
        pfad_name = getattr(getattr(content_object, "pfad", None), "name", instance.template.name)
        frist_str = task.frist.strftime("%d.%m.%Y") if task.frist else "–"
        link = f"{base_url}/workflow/task/{task.pk}/"
        betreff = f"[Vorgangswerk] Neue Aufgabe: {task.step.titel} – {vgnr}"
        text = (
            f"Guten Tag {user.get_full_name() or user.username},\n\n"
            f"Sie haben eine neue Aufgabe:\n\n"
            f"  Vorgang:  {pfad_name} – {vgnr}\n"
            f"  Schritt:  {task.step.titel}\n"
            f"  Frist:    {frist_str}\n\n"
            f"Zur Aufgabe: {link}\n\n"
            f"Mit freundlichen Grüßen\nIhr Vorgangswerk-Team"
        )
        try:
            send_mail(betreff, text, None, [user.email], fail_silently=True)
        except Exception as exc:
            logger.error("Aufgaben-E-Mail an %s fehlgeschlagen: %s", user.email, exc)

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

    def feuere_trigger(self, trigger_event: str, content_object, user) -> "WorkflowInstance | None":
        """Prueft ob ein passender aktiver Trigger existiert und startet den Workflow.

        Aufruf z.B. nach Formular-Abschluss:
            engine.feuere_trigger("antrsitzung_abgeschlossen_PARK", sitzung, sitzung.user)

        Returns:
            WorkflowInstance falls ein Workflow gestartet wurde, sonst None.
        """
        from .models import WorkflowTemplate, WorkflowTrigger
        from django.contrib.contenttypes.models import ContentType

        try:
            trigger = WorkflowTrigger.objects.select_related("content_type").get(
                trigger_event=trigger_event,
                ist_aktiv=True,
            )
        except WorkflowTrigger.DoesNotExist:
            logger.debug("Kein aktiver Trigger fuer Event '%s'.", trigger_event)
            return None

        try:
            template = WorkflowTemplate.objects.get(
                trigger_event=trigger_event,
                ist_aktiv=True,
            )
        except WorkflowTemplate.DoesNotExist:
            logger.warning("Kein aktives Template fuer trigger_event '%s'.", trigger_event)
            return None

        # Antragsteller aus content_object lesen (gem. trigger.antragsteller_pfad)
        antragsteller = user
        try:
            obj = content_object
            for teil in trigger.antragsteller_pfad.split("."):
                obj = getattr(obj, teil, None)
                if obj is None:
                    break
            if obj is not None and hasattr(obj, "pk"):
                antragsteller = obj
        except Exception:
            pass

        instance = self.start_workflow(template, content_object, antragsteller or user)
        logger.info(
            "Workflow '%s' gestartet fuer %s (Trigger: %s).",
            template.name, content_object, trigger_event,
        )
        return instance


class _FakeTask:
    """Hilfsobjekt fuer automatische Schritte ohne echten Task."""

    def __init__(self, step, instance, entscheidung):
        self.step = step
        self.instance = instance
        self.entscheidung = entscheidung
