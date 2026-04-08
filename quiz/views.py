# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Quiz-Views: Ergebnisliste, Detailansicht, Zertifikat-Verifikation, Import-Endpunkte."""
import csv
import io
import json
import logging

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from formulare.models import AntrPfad
from .models import QuizErgebnis, QuizZertifikat

logger = logging.getLogger("vorgangswerk.quiz")


# ---------------------------------------------------------------------------
# Admin: Ergebnisliste pro Pfad
# ---------------------------------------------------------------------------

@login_required
def ergebnisse(request, pfad_pk):
    pfad = get_object_or_404(AntrPfad, pk=pfad_pk)
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    qs = (
        QuizErgebnis.objects
        .filter(sitzung__pfad=pfad)
        .select_related("sitzung", "sitzung__user")
        .order_by("-erstellt_am")
    )
    bestanden_count    = qs.filter(bestanden=True).count()
    nicht_bestanden_ct = qs.filter(bestanden=False).count()
    gesamt             = qs.count()

    return render(request, "quiz/ergebnisse.html", {
        "pfad":               pfad,
        "ergebnisse":         qs,
        "bestanden_count":    bestanden_count,
        "nicht_bestanden_ct": nicht_bestanden_ct,
        "gesamt":             gesamt,
    })


# ---------------------------------------------------------------------------
# Admin: Einzelergebnis mit Detailauswertung
# ---------------------------------------------------------------------------

@login_required
def ergebnis_detail(request, pk):
    if not request.user.is_staff:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    ergebnis = get_object_or_404(
        QuizErgebnis.objects.select_related("sitzung", "sitzung__pfad", "sitzung__user"),
        pk=pk,
    )
    hat_zertifikat = hasattr(ergebnis, "zertifikat")

    return render(request, "quiz/ergebnis_detail.html", {
        "ergebnis":       ergebnis,
        "hat_zertifikat": hat_zertifikat,
    })


# ---------------------------------------------------------------------------
# Öffentlich: Zertifikat prüfen (kein Login nötig)
# ---------------------------------------------------------------------------

def zertifikat_pruefen(request, token):
    try:
        ergebnis = QuizErgebnis.objects.select_related(
            "sitzung", "sitzung__pfad"
        ).get(uuid=token)
    except QuizErgebnis.DoesNotExist:
        return render(request, "quiz/zertifikat_pruefen.html", {"ungueltig": True})

    hat_zertifikat = hasattr(ergebnis, "zertifikat")
    return render(request, "quiz/zertifikat_pruefen.html", {
        "ergebnis":       ergebnis,
        "hat_zertifikat": hat_zertifikat,
        "ungueltig":      False,
    })


# ---------------------------------------------------------------------------
# Öffentlich: Zertifikat-PDF herunterladen (kein Login nötig)
# ---------------------------------------------------------------------------

def zertifikat_download(request, token):
    try:
        ergebnis = QuizErgebnis.objects.get(uuid=token)
    except QuizErgebnis.DoesNotExist:
        raise Http404

    try:
        zertifikat = ergebnis.zertifikat
    except QuizZertifikat.DoesNotExist:
        raise Http404

    dateiname = f"Zertifikat-{ergebnis.sitzung.pfad.kuerzel}-{ergebnis.uuid}.pdf"
    response = HttpResponse(bytes(zertifikat.pdf_inhalt), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


# ---------------------------------------------------------------------------
# Import-Endpunkte (Staff only, JSON)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def fragen_aus_ki(request):
    """Generiert Quizfragen aus einem hochgeladenen PDF via Claude API."""
    if not request.user.is_staff:
        raise PermissionDenied

    pdf_file = request.FILES.get("pdf")
    if not pdf_file:
        return JsonResponse({"error": "Keine PDF-Datei übermittelt."}, status=400)

    try:
        anzahl = int(request.POST.get("anzahl", "10"))
        anzahl = max(1, min(anzahl, 30))
    except (ValueError, TypeError):
        anzahl = 10

    try:
        from .ki_generator import generiere_fragen_aus_pdf
        pdf_bytes = pdf_file.read()
        fragen = generiere_fragen_aus_pdf(pdf_bytes, anzahl=anzahl)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception("Fehler beim KI-Generieren: %s", e)
        return JsonResponse({"error": f"KI-Generierung fehlgeschlagen: {e}"}, status=500)

    return JsonResponse({"fragen": fragen})


@login_required
@require_POST
def fragen_aus_csv(request):
    """
    Importiert Quizfragen aus einer CSV-Datei.

    Erwartetes Format (Semikolon-getrennt):
    Frage;RichtigeAntwort;FalscheAntwort1;FalscheAntwort2;FalscheAntwort3;Erklaerung
    """
    if not request.user.is_staff:
        raise PermissionDenied

    csv_file = request.FILES.get("csv")
    if not csv_file:
        return JsonResponse({"error": "Keine CSV-Datei übermittelt."}, status=400)

    try:
        inhalt = csv_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            csv_file.seek(0)
            inhalt = csv_file.read().decode("latin-1")
        except Exception:
            return JsonResponse({"error": "CSV-Datei konnte nicht dekodiert werden."}, status=400)

    # Trennzeichen ermitteln
    sample = inhalt[:2000]
    trennzeichen = ";" if sample.count(";") >= sample.count(",") else ","

    reader = csv.reader(io.StringIO(inhalt), delimiter=trennzeichen)
    fragen = []
    for i, zeile in enumerate(reader):
        if i == 0 and zeile and zeile[0].lower().startswith(("frage", "question", "label")):
            continue  # Kopfzeile überspringen
        if not zeile or not zeile[0].strip():
            continue
        if len(zeile) < 2:
            continue

        label = zeile[0].strip()
        richtige = zeile[1].strip() if len(zeile) > 1 else ""
        if not richtige:
            continue

        antworten = [{"text": richtige, "korrekt": True}]
        for j in range(2, min(len(zeile), 6)):
            txt = zeile[j].strip()
            if txt and txt.lower() not in ("", "-", "erklaerung", "erklärung", "explanation"):
                antworten.append({"text": txt, "korrekt": False})

        erklaerung = ""
        if len(zeile) > 5:
            letzte = zeile[-1].strip()
            if letzte and letzte not in antworten[-1]["text"]:
                erklaerung = letzte

        fragen.append({
            "typ":         "quizfrage",
            "id":          f"csv_frage_{i}",
            "label":       label,
            "antwort_typ": "single",
            "punkte":      1.0,
            "erklaerung":  erklaerung,
            "antworten":   antworten,
            "pflicht":     True,
        })

    if not fragen:
        return JsonResponse({"error": "Keine Fragen in der CSV gefunden. Prüfen Sie das Format."}, status=400)

    return JsonResponse({"fragen": fragen})


@login_required
def demo_deck(request, name):
    """Gibt ein vorgefertigtes Demo-Deck als JSON zurück."""
    if not request.user.is_staff:
        raise PermissionDenied

    if name == "einbuergerungstest":
        try:
            anzahl = int(request.GET.get("anzahl", "20"))
            anzahl = max(5, min(anzahl, 30))
        except (ValueError, TypeError):
            anzahl = 20
        from .einbuergerungstest import get_fragen_als_felder
        fragen = get_fragen_als_felder(anzahl=anzahl)
        meta = {
            "name":        "Einbürgerungstest (BAMF)",
            "beschreibung": f"{anzahl} zufällige Fragen aus dem offiziellen BAMF-Fragenkatalog",
            "quelle":      "Bundesamt für Migration und Flüchtlinge (BAMF), § 5 UrhG",
        }
        return JsonResponse({"fragen": fragen, "meta": meta})

    return JsonResponse({"error": f"Unbekanntes Demo-Deck: {name}"}, status=404)
