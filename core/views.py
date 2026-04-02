# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""core – Views: Dashboard, Benutzerprofil."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import BenutzerprofilForm
from .models import Benutzerprofil

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    """Startseite – persoenliche Uebersicht mit Daten aus allen Apps."""
    user = request.user
    kontext = {}

    # Offene Workflow-Tasks
    try:
        from workflow.models import WorkflowInstance, WorkflowTask

        user_gruppen = user.groups.all()
        kontext["eigene_tasks"] = list(
            WorkflowTask.objects.filter(
                zugewiesen_an_user=user,
                status__in=[WorkflowTask.STATUS_OFFEN, WorkflowTask.STATUS_IN_BEARBEITUNG],
            )
            .select_related("step__template", "instance")
            .order_by("frist")[:5]
        )
        kontext["gruppen_tasks_anzahl"] = WorkflowTask.objects.filter(
            zugewiesen_an_gruppe__in=user_gruppen,
            status=WorkflowTask.STATUS_OFFEN,
            claimed_von__isnull=True,
        ).count()
        kontext["laufende_instanzen"] = WorkflowInstance.objects.filter(
            status=WorkflowInstance.STATUS_LAUFEND
        ).count()
    except Exception:
        kontext.setdefault("eigene_tasks", [])
        kontext.setdefault("gruppen_tasks_anzahl", 0)
        kontext.setdefault("laufende_instanzen", 0)

    # Meine Antraege
    try:
        from formulare.models import AntrSitzung

        kontext["meine_sitzungen"] = list(
            AntrSitzung.objects.filter(user=user)
            .select_related("pfad")
            .order_by("-gestartet_am")[:5]
        )
        kontext["offene_sitzungen"] = AntrSitzung.objects.filter(
            user=user, status__in=["gestartet", "in_bearbeitung"]
        ).count()
    except Exception:
        kontext.setdefault("meine_sitzungen", [])
        kontext.setdefault("offene_sitzungen", 0)

    # Letzte Dokumente
    try:
        from dokumente.models import Dokument

        kontext["neueste_dokumente"] = list(
            Dokument.objects.select_related("kategorie").order_by("-geaendert_am")[:5]
        )
        kontext["dokumente_gesamt"] = Dokument.objects.count()
    except Exception:
        kontext.setdefault("neueste_dokumente", [])
        kontext.setdefault("dokumente_gesamt", 0)

    # Benachrichtigungen
    try:
        from kommunikation.models import Benachrichtigung

        kontext["ungelesene"] = list(
            Benachrichtigung.objects.filter(user=user, gelesen=False)
            .order_by("-erstellt_am")[:5]
        )
        kontext["ungelesen_anzahl"] = Benachrichtigung.objects.filter(
            user=user, gelesen=False
        ).count()
    except Exception:
        kontext.setdefault("ungelesene", [])
        kontext.setdefault("ungelesen_anzahl", 0)

    # Staff: Postfach + Prozessantraege
    if user.is_staff:
        try:
            from kommunikation.models import EingehendeEmail

            kontext["neue_emails"] = list(
                EingehendeEmail.objects.filter(status=EingehendeEmail.STATUS_NEU)
                .order_by("-empfangen_am")[:5]
            )
            kontext["neue_emails_anzahl"] = EingehendeEmail.objects.filter(
                status=EingehendeEmail.STATUS_NEU
            ).count()
        except Exception:
            kontext.setdefault("neue_emails", [])
            kontext.setdefault("neue_emails_anzahl", 0)

        try:
            from workflow.models import ProzessAntrag

            kontext["offene_prozessantraege"] = ProzessAntrag.objects.filter(
                status__in=["eingereicht", "in_pruefung"]
            ).count()
        except Exception:
            kontext.setdefault("offene_prozessantraege", 0)

    return render(request, "core/dashboard.html", kontext)


@login_required
def profil(request):
    """Benutzerprofil anzeigen und bearbeiten."""
    profil_obj, _ = Benutzerprofil.objects.get_or_create(user=request.user)
    form = BenutzerprofilForm(request.POST or None, instance=profil_obj)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profil gespeichert.")
        return redirect("core:profil")

    return render(request, "core/profil.html", {"form": form, "profil": profil_obj})
