# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""core – Views: Dashboard, Benutzerprofil."""
import logging
import urllib.request
import urllib.parse
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

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

    kontext["zeige_staff_bereich"] = (
        user.is_staff
        or user.groups.filter(name="Sachbearbeiter").exists()
    )

    # Onboarding-Card: anzeigen wenn System noch leer ist
    if user.is_staff:
        try:
            from formulare.models import AntrPfad
            from workflow.models import WorkflowTemplate
            keine_pfade = not AntrPfad.objects.exists()
            keine_workflows = not WorkflowTemplate.objects.exists()
            kontext["zeige_onboarding"] = keine_pfade and keine_workflows
        except Exception:
            kontext["zeige_onboarding"] = False
    else:
        kontext["zeige_onboarding"] = False

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


# ---------------------------------------------------------------------------
# LeiKa-Autocomplete
# Hinweis: PVOG-API URL wechselt am 1. August 2026 auf pvog.fitko.net
# ---------------------------------------------------------------------------

# Neue URL ab August 2026: https://pvog.fitko.net/suchdienst/api/v1/...
_PVOG_SUGGESTIONS_URL = (
    "https://pvog.fitko.net/suchdienst/api/v1"
    "/servicedescriptions/suggestions/020000000000"
)


@login_required
@require_GET
def leika_autocomplete(request):
    """
    Gibt LeiKa-Vorschläge zurück: zuerst lokale Treffer (mit Schlüssel),
    dann PVOG-Textvorschläge als Ergänzung.
    """
    q = request.GET.get("q", "").strip().lower()
    if len(q) < 2:
        return JsonResponse([], safe=False)

    from formulare.leika_data import LEIKA_LEISTUNGEN

    # 1. Lokale Suche (hat LeiKa-Schlüssel)
    lokal = []
    for l in LEIKA_LEISTUNGEN:
        if q in l["name"].lower():
            lokal.append({
                "schluessel": l["schluessel"],
                "name": l["name"],
                "quelle": "lokal",
            })

    lokal_namen = {e["name"].lower() for e in lokal}

    # 2. PVOG-Suggestions (nur Text, kein Schlüssel – als Hinweis auf fimportal.de)
    pvog = []
    try:
        url = f"{_PVOG_SUGGESTIONS_URL}?{urllib.parse.urlencode({'q': q})}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            vorschlaege = json.loads(resp.read().decode())
            for v in vorschlaege[:8]:
                text = v.get("suggestedText", "")
                if text.lower() not in lokal_namen:
                    pvog.append({
                        "schluessel": None,
                        "name": text,
                        "quelle": "pvog",
                    })
    except Exception:
        pass  # PVOG nicht erreichbar → nur lokale Treffer

    return JsonResponse(lokal[:6] + pvog[:4], safe=False)


@login_required
def ueber(request):
    """Über Vorgangswerk – Motivationsseite mit Feature-Übersicht."""
    from formulare.models import AntrPfad, AntrSitzung
    from workflow.models import WorkflowTemplate
    from korrespondenz.models import Briefvorgang
    stats = {
        "formulare": AntrPfad.objects.filter(aktiv=True).count(),
        "antraege": AntrSitzung.objects.filter(status="abgeschlossen").count(),
        "workflows": WorkflowTemplate.objects.filter(ist_aktiv=True).count(),
        "briefe": Briefvorgang.objects.count(),
    }
    return render(request, "core/ueber.html", {"stats": stats})


def roadmap(request):
    """Innovationsboard – Roadmap und nutzbare Standards."""
    from .models import RoadmapEintrag
    eintraege = RoadmapEintrag.objects.all()

    # Filter
    status = request.GET.get("status", "")
    kategorie = request.GET.get("kategorie", "")
    if status:
        eintraege = eintraege.filter(status=status)
    if kategorie:
        eintraege = eintraege.filter(kategorie=kategorie)

    return render(request, "core/roadmap.html", {
        "eintraege": eintraege,
        "status_choices": RoadmapEintrag.STATUS_CHOICES,
        "kategorie_choices": RoadmapEintrag.KATEGORIE_CHOICES,
        "filter_status": status,
        "filter_kategorie": kategorie,
    })
