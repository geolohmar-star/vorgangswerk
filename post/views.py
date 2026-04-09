# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

import csv
import io
import zipfile

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import PosteintragForm
from .models import Organisation, Posteintrag, VerteilEmpfaenger


@login_required
def postbuch_liste(request):
    qs = Posteintrag.objects.select_related(
        "erstellt_von", "dokument", "eingehende_email", "briefvorgang"
    )

    # Filter
    richtung = request.GET.get("richtung", "")
    typ = request.GET.get("typ", "")
    q = request.GET.get("q", "").strip()
    datum_von = request.GET.get("datum_von", "")
    datum_bis = request.GET.get("datum_bis", "")

    if richtung:
        qs = qs.filter(richtung=richtung)
    if typ:
        qs = qs.filter(typ=typ)
    if q:
        qs = qs.filter(
            betreff__icontains=q
        ) | qs.filter(
            absender_empfaenger__icontains=q
        ) | qs.filter(
            vorgang_bezug__icontains=q
        ) | qs.filter(
            lfd_nr__icontains=q
        )
        qs = qs.distinct()
    if datum_von:
        try:
            qs = qs.filter(datum__gte=datum_von)
        except Exception:
            pass
    if datum_bis:
        try:
            qs = qs.filter(datum__lte=datum_bis)
        except Exception:
            pass

    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "post/postbuch_liste.html", {
        "page_obj": page,
        "richtung_choices": Posteintrag.RICHTUNG_CHOICES,
        "typ_choices": Posteintrag.TYP_CHOICES,
        "filter_richtung": richtung,
        "filter_typ": typ,
        "filter_q": q,
        "filter_datum_von": datum_von,
        "filter_datum_bis": datum_bis,
        "gesamt": qs.count(),
    })


@login_required
def posteintrag_neu(request):
    form = PosteintragForm(request.POST or None, initial={
        "datum": timezone.now().date(),
        "richtung": request.GET.get("richtung", Posteintrag.RICHTUNG_AUSGANG),
    })
    if request.method == "POST" and form.is_valid():
        eintrag = form.save(commit=False)
        eintrag.erstellt_von = request.user
        eintrag.save()
        return redirect("post:liste")
    return render(request, "post/posteintrag_form.html", {"form": form, "neu": True})


@login_required
def posteintrag_bearbeiten(request, pk):
    eintrag = get_object_or_404(Posteintrag, pk=pk)
    form = PosteintragForm(request.POST or None, instance=eintrag)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("post:liste")
    return render(request, "post/posteintrag_form.html", {"form": form, "eintrag": eintrag})


@login_required
def posteintrag_loeschen(request, pk):
    eintrag = get_object_or_404(Posteintrag, pk=pk)
    if request.method == "POST":
        eintrag.delete()
        return redirect("post:liste")
    return render(request, "post/posteintrag_loeschen.html", {"eintrag": eintrag})


# ---------------------------------------------------------------------------
# Verteiler-Quittierung
# ---------------------------------------------------------------------------

def verteiler_bestaetigung(request, token):
    """Oeffentlicher Endpunkt: Empfaenger klickt Bestaetigunslink."""
    empfaenger = get_object_or_404(VerteilEmpfaenger, token=token)

    bereits_bestaetigt = empfaenger.status == VerteilEmpfaenger.STATUS_BESTAETIGT

    if not bereits_bestaetigt:
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if not ip:
            ip = request.META.get("REMOTE_ADDR")
        empfaenger.status = VerteilEmpfaenger.STATUS_BESTAETIGT
        empfaenger.bestaetigt_am = timezone.now()
        empfaenger.bestaetigung_ip = ip or None
        empfaenger.save(update_fields=["status", "bestaetigt_am", "bestaetigung_ip"])

    task = empfaenger.workflow_task
    return render(request, "post/verteiler_bestaetigung.html", {
        "empfaenger": empfaenger,
        "task": task,
        "bereits_bestaetigt": bereits_bestaetigt,
    })


@login_required
def verteiler_manuell_erledigt(request, pk):
    """Bearbeiter markiert einen Brief-Empfaenger manuell als erledigt."""
    empfaenger = get_object_or_404(VerteilEmpfaenger, pk=pk)
    if request.method == "POST":
        empfaenger.status = VerteilEmpfaenger.STATUS_MANUELL
        empfaenger.bestaetigt_am = timezone.now()
        empfaenger.save(update_fields=["status", "bestaetigt_am"])
    return redirect("workflow:task_detail", pk=empfaenger.workflow_task_id)


@login_required
def verteiler_erneut_senden(request, pk):
    """Bearbeiter sendet die E-Mail fuer einen Empfaenger erneut."""
    from django.conf import settings
    from django.core.mail import EmailMessage
    empfaenger = get_object_or_404(VerteilEmpfaenger, pk=pk)
    if request.method == "POST" and empfaenger.email:
        base_url = getattr(settings, "VORGANGSWERK_BASE_URL", "http://localhost:8100")
        bestaetigung_url = f"{base_url}/postbuch/bestaetigung/{empfaenger.token}/"
        task = empfaenger.workflow_task
        mail = EmailMessage(
            subject=f"Verteiler: {task.step.titel}",
            body=(
                f"Sie erhalten hiermit eine Kopie des Vorgangs '{task.step.titel}'.\n\n"
                f"Bitte bestaetigen Sie den Erhalt durch Klick auf folgenden Link:\n"
                f"{bestaetigung_url}\n\n"
                f"Vorgangswerk"
            ),
            to=[empfaenger.email],
        )
        try:
            mail.send(fail_silently=False)
            empfaenger.status = VerteilEmpfaenger.STATUS_VERSENDET
            empfaenger.versendet_am = timezone.now()
            empfaenger.save(update_fields=["status", "versendet_am"])
        except Exception:
            pass
    return redirect("workflow:task_detail", pk=empfaenger.workflow_task_id)


@login_required
def postbuch_csv(request):
    """CSV-Export des Postbuchs (respektiert aktive Filter)."""
    qs = Posteintrag.objects.select_related("erstellt_von").order_by("datum", "lfd_nr")

    richtung  = request.GET.get("richtung", "")
    typ       = request.GET.get("typ", "")
    q         = request.GET.get("q", "").strip()
    datum_von = request.GET.get("datum_von", "")
    datum_bis = request.GET.get("datum_bis", "")

    if richtung:
        qs = qs.filter(richtung=richtung)
    if typ:
        qs = qs.filter(typ=typ)
    if q:
        qs = (
            qs.filter(betreff__icontains=q)
            | qs.filter(absender_empfaenger__icontains=q)
            | qs.filter(vorgang_bezug__icontains=q)
            | qs.filter(lfd_nr__icontains=q)
        ).distinct()
    if datum_von:
        try:
            qs = qs.filter(datum__gte=datum_von)
        except Exception:
            pass
    if datum_bis:
        try:
            qs = qs.filter(datum__lte=datum_bis)
        except Exception:
            pass

    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    heute = timezone.localdate().strftime("%Y%m%d")
    response["Content-Disposition"] = f'attachment; filename="postbuch_{heute}.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow([
        "Tagebuch-Nr.", "Datum", "Richtung", "Typ",
        "Absender / Empfaenger", "Betreff",
        "Vorgangsbezug", "Notiz", "Erstellt von", "Erstellt am",
    ])
    for e in qs:
        writer.writerow([
            e.lfd_nr,
            e.datum.strftime("%d.%m.%Y"),
            e.get_richtung_display(),
            e.get_typ_display(),
            e.absender_empfaenger,
            e.betreff,
            e.vorgang_bezug,
            e.notiz,
            e.erstellt_von.get_full_name() if e.erstellt_von else "",
            e.erstellt_am.strftime("%d.%m.%Y %H:%M"),
        ])
    return response


# ---------------------------------------------------------------------------
# Organisationsverzeichnis
# ---------------------------------------------------------------------------

@login_required
def org_liste(request):
    q   = request.GET.get("q", "").strip()
    typ = request.GET.get("typ", "")
    qs  = Organisation.objects.all()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(ort__icontains=q) | qs.filter(email__icontains=q)
        qs = qs.distinct()
    if typ:
        qs = qs.filter(typ=typ)
    return render(request, "post/org_liste.html", {
        "orgs": qs,
        "typ_choices": Organisation.TYP_CHOICES,
        "filter_q": q,
        "filter_typ": typ,
    })


@login_required
def org_neu(request):
    from .forms import OrganisationForm
    form = OrganisationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("post:org_liste")
    return render(request, "post/org_form.html", {"form": form, "neu": True})


@login_required
def org_bearbeiten(request, pk):
    from .forms import OrganisationForm
    org = get_object_or_404(Organisation, pk=pk)
    form = OrganisationForm(request.POST or None, instance=org)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("post:org_liste")
    return render(request, "post/org_form.html", {"form": form, "org": org})


@login_required
def org_loeschen(request, pk):
    org = get_object_or_404(Organisation, pk=pk)
    if request.method == "POST":
        org.delete()
        return redirect("post:org_liste")
    return render(request, "post/org_loeschen.html", {"org": org})


@login_required
def org_autocomplete(request):
    """JSON-Autocomplete fuer Verteiler-Konfiguration."""
    from django.http import JsonResponse
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse([], safe=False)
    qs = Organisation.objects.filter(name__icontains=q)[:10]
    return JsonResponse([
        {"id": o.pk, "name": o.name, "email": o.email, "typ": o.get_typ_display()}
        for o in qs
    ], safe=False)
