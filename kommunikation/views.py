# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Kommunikation-App Views: Postfach, E-Mail-Detail, Benachrichtigungen."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Benachrichtigung, EingehendeEmail, EmailAnhang

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Postfach
# ---------------------------------------------------------------------------


@login_required
def postfach(request):
    """Eingehende E-Mails / Postfach-Uebersicht (nur Staff)."""
    if not request.user.is_staff:
        messages.error(request, "Keine Berechtigung.")
        return redirect("core:dashboard")

    status_filter = request.GET.get("status", "")
    suche = request.GET.get("q", "").strip()

    qs = EingehendeEmail.objects.select_related("zugewiesen_an")

    if status_filter:
        qs = qs.filter(status=status_filter)
    else:
        # Standardmaessig nicht-archivierte anzeigen
        qs = qs.exclude(status=EingehendeEmail.STATUS_ARCHIVIERT)

    if suche:
        qs = qs.filter(betreff__icontains=suche) | EingehendeEmail.objects.filter(
            absender_email__icontains=suche
        ).exclude(status=EingehendeEmail.STATUS_ARCHIVIERT)

    kontext = {
        "emails": qs.order_by("-empfangen_am"),
        "status_filter": status_filter,
        "suche": suche,
        "status_choices": EingehendeEmail.STATUS_CHOICES,
        "anzahl_neu": EingehendeEmail.objects.filter(status=EingehendeEmail.STATUS_NEU).count(),
    }
    return render(request, "kommunikation/postfach.html", kontext)


@login_required
def email_detail(request, pk):
    """Detail-Ansicht einer eingehenden E-Mail."""
    if not request.user.is_staff:
        messages.error(request, "Keine Berechtigung.")
        return redirect("core:dashboard")

    email_obj = get_object_or_404(
        EingehendeEmail.objects.prefetch_related("anhaenge").select_related("zugewiesen_an"),
        pk=pk,
    )

    # Automatisch als gelesen markieren
    if email_obj.status == EingehendeEmail.STATUS_NEU:
        email_obj.status = EingehendeEmail.STATUS_GELESEN
        email_obj.save(update_fields=["status"])

    if request.method == "POST":
        aktion = request.POST.get("aktion")
        if aktion == "archivieren":
            email_obj.status = EingehendeEmail.STATUS_ARCHIVIERT
            email_obj.save(update_fields=["status"])
            messages.success(request, "E-Mail archiviert.")
            return redirect("kommunikation:postfach")
        elif aktion == "zuweisen":
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user_id = request.POST.get("user_id")
            try:
                zugewiesen_an = User.objects.get(pk=user_id)
                email_obj.zugewiesen_an = zugewiesen_an
                email_obj.status = EingehendeEmail.STATUS_ZUGEWIESEN
                email_obj.save(update_fields=["zugewiesen_an", "status"])
                messages.success(request, f"E-Mail an {zugewiesen_an.username} zugewiesen.")
            except User.DoesNotExist:
                messages.error(request, "Benutzer nicht gefunden.")
        elif aktion == "notiz":
            email_obj.notiz = request.POST.get("notiz", "")
            email_obj.save(update_fields=["notiz"])
            messages.success(request, "Notiz gespeichert.")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    benutzer = User.objects.filter(is_active=True).order_by("username")

    kontext = {
        "email_obj": email_obj,
        "benutzer": benutzer,
    }
    return render(request, "kommunikation/email_detail.html", kontext)


@login_required
def anhang_download(request, pk):
    """Laedt einen E-Mail-Anhang herunter."""
    if not request.user.is_staff:
        messages.error(request, "Keine Berechtigung.")
        return redirect("core:dashboard")

    anhang = get_object_or_404(EmailAnhang, pk=pk)
    response = HttpResponse(
        bytes(anhang.inhalt),
        content_type=anhang.dateityp or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{anhang.dateiname}"'
    return response


# ---------------------------------------------------------------------------
# Benachrichtigungen
# ---------------------------------------------------------------------------


@login_required
def benachrichtigungen(request):
    """Liste aller Benachrichtigungen des eingeloggten Benutzers."""
    nachrichten = Benachrichtigung.objects.filter(user=request.user).order_by("-erstellt_am")
    ungelesen = nachrichten.filter(gelesen=False).count()
    return render(request, "kommunikation/benachrichtigungen.html", {
        "nachrichten": nachrichten,
        "ungelesen": ungelesen,
    })


@login_required
@require_POST
def benachrichtigung_gelesen(request, pk):
    """Markiert eine Benachrichtigung als gelesen."""
    b = get_object_or_404(Benachrichtigung, pk=pk, user=request.user)
    b.als_gelesen_markieren()
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect("kommunikation:benachrichtigungen")


@login_required
@require_POST
def alle_gelesen(request):
    """Markiert alle Benachrichtigungen des Users als gelesen."""
    from django.utils import timezone
    Benachrichtigung.objects.filter(user=request.user, gelesen=False).update(
        gelesen=True,
        gelesen_am=timezone.now(),
    )
    if request.headers.get("HX-Request"):
        return HttpResponse("")
    return redirect("kommunikation:benachrichtigungen")


@login_required
def benachrichtigungen_count(request):
    """Gibt die Anzahl ungelesener Benachrichtigungen als JSON zurueck (fuer Navbar-Badge)."""
    count = Benachrichtigung.objects.filter(user=request.user, gelesen=False).count()
    return JsonResponse({"count": count})


# ---------------------------------------------------------------------------
# HTMX-Partials fuer Navbar-Badge
# ---------------------------------------------------------------------------


@login_required
def navbar_badge(request):
    """Gibt den Benachrichtigungs-Badge als HTML-Partial zurueck."""
    count = Benachrichtigung.objects.filter(user=request.user, gelesen=False).count()
    return render(request, "kommunikation/partials/_navbar_badge.html", {"count": count})
