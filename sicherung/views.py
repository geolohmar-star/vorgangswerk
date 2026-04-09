# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Sicherungs-Statusseite (nur Staff)."""
import subprocess
from pathlib import Path

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import SicherungsProtokoll
from .management.commands.sicherung_erstellen import SICHERUNGS_DIR, AUFBEWAHRUNG


@staff_member_required
def uebersicht(request):
    protokolle = SicherungsProtokoll.objects.all()[:50]

    # Letzte erfolgreiche Sicherung pro Typ
    letzte = {}
    for typ in ["datenbank", "dateien", "komplett"]:
        letzte[typ] = (
            SicherungsProtokoll.objects
            .filter(typ=typ, status__in=["ok", "geprueft"])
            .order_by("-erstellt_am")
            .first()
        )

    # Sicherungsverzeichnis-Info
    try:
        sicherungs_pfad = Path("/app/sicherungen")
        dateien_anzahl = len(list(sicherungs_pfad.glob("*.tar.gz*"))) if sicherungs_pfad.exists() else 0
    except Exception:
        dateien_anzahl = 0

    return render(request, "sicherung/uebersicht.html", {
        "protokolle": protokolle,
        "letzte": letzte,
        "aufbewahrung": AUFBEWAHRUNG,
        "dateien_anzahl": dateien_anzahl,
    })


@staff_member_required
@require_POST
def sicherung_starten(request):
    """Löst eine manuelle Sicherung aus."""
    typ = request.POST.get("typ", "komplett")
    if typ not in ("datenbank", "dateien", "komplett"):
        messages.error(request, "Ungültiger Sicherungstyp.")
        return redirect("sicherung:uebersicht")

    try:
        from django.core.management import call_command
        call_command("sicherung_erstellen", typ=typ, rhythmus="manuell")
        messages.success(request, f"Sicherung ({typ}) erfolgreich erstellt.")
    except SystemExit:
        messages.error(request, "Sicherung fehlgeschlagen. Details im Protokoll.")
    except Exception as e:
        messages.error(request, f"Fehler: {e}")

    return redirect("sicherung:uebersicht")


@staff_member_required
@require_POST
def integritaet_pruefen(request, pk):
    """Prüft die Integrität einer einzelnen Sicherung."""
    try:
        from django.core.management import call_command
        call_command("sicherung_pruefen", pk=pk)
        messages.success(request, "Integrität bestätigt – SHA-256 stimmt.")
    except SystemExit:
        messages.error(request, "Integritätsprüfung fehlgeschlagen!")
    except Exception as e:
        messages.error(request, f"Fehler: {e}")

    return redirect("sicherung:uebersicht")


@staff_member_required
def wiederherstellen(request, pk):
    """Bestätigungsseite + Restore-Ausführung."""
    protokoll = SicherungsProtokoll.objects.get(pk=pk)

    if request.method == "POST":
        if request.POST.get("bestaetigung") != "WIEDERHERSTELLEN":
            messages.error(request, "Bestätigung falsch – bitte genau 'WIEDERHERSTELLEN' eingeben.")
            return redirect("sicherung:wiederherstellen", pk=pk)
        try:
            from django.core.management import call_command
            call_command("sicherung_wiederherstellen", pk=pk)
            messages.success(request, f"Wiederherstellung aus Sicherung #{pk} erfolgreich.")
        except Exception as e:
            messages.error(request, f"Fehler: {e}")
        return redirect("sicherung:uebersicht")

    return render(request, "sicherung/wiederherstellen.html", {"protokoll": protokoll})
