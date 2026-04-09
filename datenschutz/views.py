# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Datenschutz-Views: DSGVO Art. 15 Selbstauskunft, Löschprotokolle.
"""
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Loeschprotokoll

logger = logging.getLogger("vorgangswerk.datenschutz")


@login_required
def dashboard(request):
    """DSGVO-Übersicht: Selbstauskunft, Löschprotokolle (Staff)."""
    protokolle = None
    if request.user.is_staff:
        protokolle = Loeschprotokoll.objects.all()[:50]
    return render(request, "datenschutz/dashboard.html", {
        "protokolle": protokolle,
    })


@login_required
def auskunft_pdf(request):
    """DSGVO Art. 15 – Selbstauskunft: alle über den eingeloggten User
    gespeicherten Daten als PDF-Download."""
    from weasyprint import HTML
    from django.template.loader import render_to_string

    kontext = _sammle_auskunftsdaten(request.user)
    kontext["auskunft_datum"] = timezone.now()

    html_str = render_to_string("datenschutz/auskunft_pdf.html", kontext)
    pdf = HTML(string=html_str, base_url=request.build_absolute_uri("/")).write_pdf()

    dateiname = f"DSGVO_Auskunft_{request.user.username}_{timezone.now().date()}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


@login_required
def auskunft_suche(request):
    """DSGVO Art. 15 – Staff-Suche: Antragsdaten einer Person abrufen."""
    if not request.user.is_staff:
        return HttpResponseForbidden("Nur für Administratoren.")

    suche = request.GET.get("q", "").strip()
    geburtsdatum_raw = request.GET.get("geburtsdatum", "").strip()
    geburtsdatum_iso = _parse_geburtsdatum(geburtsdatum_raw)

    sitzungen = _suche_sitzungen(suche, geburtsdatum_iso)

    return render(request, "datenschutz/auskunft_suche.html", {
        "suche": suche,
        "geburtsdatum": geburtsdatum_raw,
        "sitzungen": sitzungen,
        "gesamt": len(sitzungen),
    })


@login_required
def auskunft_suche_pdf(request):
    """DSGVO Art. 15 – PDF-Export der Suchergebnisse (nur Staff)."""
    if not request.user.is_staff:
        return HttpResponseForbidden("Nur für Administratoren.")

    from weasyprint import HTML
    from django.template.loader import render_to_string

    suche = request.GET.get("q", "").strip()
    geburtsdatum_raw = request.GET.get("geburtsdatum", "").strip()
    geburtsdatum_iso = _parse_geburtsdatum(geburtsdatum_raw)
    sitzungen = _suche_sitzungen(suche, geburtsdatum_iso)

    kontext = {
        "suche": suche,
        "geburtsdatum": geburtsdatum_raw,
        "sitzungen": sitzungen,
        "gesamt": len(sitzungen),
        "auskunft_datum": timezone.now(),
        "erstellt_von": request.user,
    }
    html_str = render_to_string("datenschutz/auskunft_suche_pdf.html", kontext)
    pdf = HTML(string=html_str, base_url=request.build_absolute_uri("/")).write_pdf()

    dateiname = f"DSGVO_Auskunft_{suche}_{timezone.now().date()}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


@login_required
def loeschprotokoll_detail(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Nur für Administratoren.")
    protokoll = get_object_or_404(Loeschprotokoll, pk=pk)
    return render(request, "datenschutz/loeschprotokoll_detail.html", {
        "protokoll": protokoll,
    })


@login_required
def loeschprotokoll_pdf_download(request, pk):
    if not request.user.is_staff:
        return HttpResponse(status=403)
    protokoll = get_object_or_404(Loeschprotokoll, pk=pk)
    if not protokoll.protokoll_pdf:
        return HttpResponse(status=404)
    response = HttpResponse(bytes(protokoll.protokoll_pdf), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="Loeschprotokoll_{protokoll.pk}.pdf"'
    )
    return response


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _parse_geburtsdatum(raw):
    raw = (raw or "").strip()
    if not raw:
        return ""
    if len(raw) == 10 and raw[2] == "." and raw[5] == ".":
        try:
            tag, monat, jahr = raw.split(".")
            return f"{jahr}-{monat}-{tag}"
        except ValueError:
            return ""
    if len(raw) == 10 and raw[4] == "-":
        return raw
    return ""


def _suche_sitzungen(suche, geburtsdatum_iso):
    """Durchsucht AntrSitzungen nach Name, E-Mail oder Vorgangsnummer."""
    if not suche:
        return []

    from formulare.models import AntrSitzung
    treffer = []
    qs = AntrSitzung.objects.select_related("pfad", "user").filter(
        status=AntrSitzung.STATUS_ABGESCHLOSSEN
    )
    for s in qs:
        daten_str = str(s.gesammelte_daten or {}).lower()
        email = (s.email_anonym or "").lower()
        vorgangsnr = (s.vorgangsnummer or "").lower()
        user_str = str(s.user or "").lower()
        if not (
            suche.lower() in daten_str
            or suche.lower() in email
            or suche.lower() in vorgangsnr
            or suche.lower() in user_str
        ):
            continue
        if geburtsdatum_iso:
            geb = (s.gesammelte_daten or {}).get("geburtsdatum_datum", "")
            if geb != geburtsdatum_iso:
                continue
        treffer.append({"sitzung": s})
    return treffer[:100]


def _sammle_auskunftsdaten(user):
    """Sammelt alle personenbezogenen Daten eines Users für die DSGVO-Auskunft."""
    daten = {"user": user, "kategorien": []}

    # Stammdaten
    daten["kategorien"].append({
        "titel": "Stammdaten",
        "rechtsgrundlage": "Art. 6 Abs. 1 lit. b DSGVO",
        "speicherfrist": "Bis zur Konto-Löschung",
        "felder": [
            ("Benutzername", user.username),
            ("E-Mail", user.email),
            ("Vorname", user.first_name or "–"),
            ("Nachname", user.last_name or "–"),
            ("Konto aktiv", "Ja" if user.is_active else "Nein"),
            ("Registriert am", user.date_joined.strftime("%d.%m.%Y")),
            ("Letzter Login", user.last_login.strftime("%d.%m.%Y %H:%M") if user.last_login else "–"),
        ],
    })

    # Antragssitzungen
    try:
        from formulare.models import AntrSitzung
        sitzungen = AntrSitzung.objects.filter(user=user)
        daten["kategorien"].append({
            "titel": "Antragssitzungen",
            "rechtsgrundlage": "Art. 6 Abs. 1 lit. e DSGVO (öffentliche Aufgabe)",
            "speicherfrist": "Gemäß Aufbewahrungsfristen der Behörde",
            "anzahl": sitzungen.count(),
            "zeitraum": _zeitraum(sitzungen, "erstellt_am"),
        })
    except Exception:
        pass

    # Workflow-Aufgaben
    try:
        from workflow.models import WorkflowTask
        tasks = WorkflowTask.objects.filter(zugewiesen_an=user)
        daten["kategorien"].append({
            "titel": "Workflow-Aufgaben",
            "rechtsgrundlage": "Art. 6 Abs. 1 lit. b DSGVO",
            "speicherfrist": "3 Jahre (§ 195 BGB)",
            "anzahl": tasks.count(),
            "zeitraum": _zeitraum(tasks, "erstellt_am"),
        })
    except Exception:
        pass

    # Dokumente
    try:
        from dokumente.models import Dokument
        dokumente = Dokument.objects.filter(erstellt_von=user)
        daten["kategorien"].append({
            "titel": "Dokumente",
            "rechtsgrundlage": "Art. 6 Abs. 1 lit. b DSGVO",
            "speicherfrist": "Gemäß Dokumentenklasse",
            "anzahl": dokumente.count(),
            "zeitraum": _zeitraum(dokumente, "erstellt_am"),
        })
    except Exception:
        pass

    # Digitale Signaturen
    try:
        from signatur.models import SignaturProtokoll, MitarbeiterZertifikat
        protokolle = SignaturProtokoll.objects.filter(unterzeichner=user)
        zertifikate = MitarbeiterZertifikat.objects.filter(user=user)
        daten["kategorien"].append({
            "titel": "Digitale Signaturen & Zertifikate",
            "rechtsgrundlage": "Art. 6 Abs. 1 lit. c DSGVO / eIDAS",
            "speicherfrist": "10 Jahre (eIDAS Art. 40)",
            "anzahl": protokolle.count() + zertifikate.count(),
            "details": f"{zertifikate.count()} Zertifikat(e), {protokolle.count()} Signatur-Protokoll(e)",
        })
    except Exception:
        pass

    return daten


def _zeitraum(queryset, datumsfeld):
    from django.db.models import Min, Max
    agg = queryset.aggregate(von=Min(datumsfeld), bis=Max(datumsfeld))
    if not agg["von"]:
        return "–"
    von, bis = agg["von"], agg["bis"]
    von_str = von.date().strftime("%d.%m.%Y") if hasattr(von, "date") else str(von)
    bis_str = bis.date().strftime("%d.%m.%Y") if hasattr(bis, "date") else str(bis)
    return f"{von_str} – {bis_str}"
