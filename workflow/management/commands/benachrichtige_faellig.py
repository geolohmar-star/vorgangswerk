# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Management-Command: E-Mail-Erinnerung fuer ueberfaellige Workflow-Tasks."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sendet E-Mail-Erinnerungen fuer ueberfaellige Workflow-Tasks."

    def handle(self, *args, **options):
        from workflow.models import WorkflowTask

        jetzt = timezone.now()
        faellige = WorkflowTask.objects.filter(
            status__in=[WorkflowTask.STATUS_OFFEN, WorkflowTask.STATUS_IN_BEARBEITUNG],
            frist__lt=jetzt,
        ).select_related("step", "instance__template", "zugewiesen_an_user", "zugewiesen_an_gruppe")

        base_url = getattr(settings, "VORGANGSWERK_BASE_URL", "").rstrip("/")
        gesendet = 0

        for task in faellige:
            empfaenger = []
            if task.zugewiesen_an_user:
                empfaenger = [task.zugewiesen_an_user]
            elif task.zugewiesen_an_gruppe:
                empfaenger = list(task.zugewiesen_an_gruppe.user_set.filter(is_active=True))

            for user in empfaenger:
                if not user.email:
                    continue
                try:
                    profil = user.profil
                    if not profil.email_bei_faelligkeit:
                        continue
                except Exception:
                    pass

                content_object = task.instance.content_object
                vgnr = getattr(content_object, "vorgangsnummer", "") or f"#{task.instance.pk}"
                pfad_name = getattr(getattr(content_object, "pfad", None), "name", task.instance.template.name)
                link = f"{base_url}/workflow/task/{task.pk}/"
                tage = (jetzt - task.frist).days

                betreff = f"[Vorgangswerk] Erinnerung: Aufgabe überfällig – {vgnr}"
                text = (
                    f"Guten Tag {user.get_full_name() or user.username},\n\n"
                    f"folgende Aufgabe ist seit {tage} Tag(en) überfällig:\n\n"
                    f"  Vorgang:  {pfad_name} – {vgnr}\n"
                    f"  Schritt:  {task.step.titel}\n"
                    f"  Frist war: {task.frist.strftime('%d.%m.%Y')}\n\n"
                    f"Zur Aufgabe: {link}\n\n"
                    f"Mit freundlichen Grüßen\nIhr Vorgangswerk-Team"
                )
                try:
                    send_mail(betreff, text, None, [user.email], fail_silently=True)
                    gesendet += 1
                except Exception as exc:
                    logger.error("Faelligkeits-Mail an %s fehlgeschlagen: %s", user.email, exc)

        self.stdout.write(self.style.SUCCESS(f"{gesendet} Erinnerungs-E-Mail(s) gesendet."))
