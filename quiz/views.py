# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Quiz-Views: Ergebnisliste, Detailansicht, Zertifikat-Verifikation, Import-Endpunkte."""
import csv
import io
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from formulare.models import AntrPfad
from .models import QuizErgebnis, QuizZertifikat, QuizFragenPool

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
            "name":        "Einbürgerungstest Demo",
            "beschreibung": f"{anzahl} Fragen aus dem Demo-Deck",
            "quelle":      "Bundesamt für Migration und Flüchtlinge (BAMF), § 5 UrhG",
        }
        return JsonResponse({"fragen": fragen, "meta": meta})

    if name == "bamf":
        from .bamf_fragen import BUNDESWEIT, _zu_quizfelder
        fragen = _zu_quizfelder(list(BUNDESWEIT), "bamf")
        meta = {
            "name":        "BAMF Einbürgerungstest",
            "beschreibung": f"{len(fragen)} bundesweite Fragen",
            "quelle":      "Bundesamt für Migration und Flüchtlinge (BAMF), § 5 UrhG",
        }
        return JsonResponse({"fragen": fragen, "meta": meta})

    return JsonResponse({"error": f"Unbekanntes Demo-Deck: {name}"}, status=404)


# ---------------------------------------------------------------------------
# Fragenpool-Verwaltung (Staff only)
# ---------------------------------------------------------------------------

def _ist_staff(request):
    return request.user.is_authenticated and request.user.is_staff


@login_required
def pool_liste(request):
    """Übersicht aller Fragenpools."""
    if not _ist_staff(request):
        raise PermissionDenied
    pools = QuizFragenPool.objects.all()
    return render(request, "quiz/pool_liste.html", {"pools": pools})


@login_required
def pool_detail(request, pk):
    """Detailansicht: Fragen eines Pools anzeigen und bearbeiten."""
    if not _ist_staff(request):
        raise PermissionDenied
    pool = get_object_or_404(QuizFragenPool, pk=pk)
    from .bamf_fragen import BUNDESWEIT
    return render(request, "quiz/pool_detail.html", {
        "pool": pool,
        "bamf_anzahl": len(BUNDESWEIT),
    })


@login_required
@require_POST
def pool_neu(request):
    """Neuen leeren Pool anlegen."""
    if not _ist_staff(request):
        raise PermissionDenied
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name ist Pflichtfeld.")
        return redirect("quiz:pool_liste")
    pool = QuizFragenPool.objects.create(
        name=name,
        beschreibung=request.POST.get("beschreibung", "").strip(),
    )
    messages.success(request, f'Pool „{pool.name}" angelegt.')
    return redirect("quiz:pool_detail", pk=pool.pk)


@login_required
@require_POST
def pool_loeschen(request, pk):
    """Pool löschen."""
    if not _ist_staff(request):
        raise PermissionDenied
    pool = get_object_or_404(QuizFragenPool, pk=pk)
    name = pool.name
    pool.delete()
    messages.success(request, f'Pool „{name}" gelöscht.')
    return redirect("quiz:pool_liste")


@login_required
@require_POST
def pool_fragen_speichern(request, pk):
    """Ersetzt fragen_json eines Pools (JSON-Body mit {fragen: [...]})."""
    if not _ist_staff(request):
        raise PermissionDenied
    pool = get_object_or_404(QuizFragenPool, pk=pk)
    try:
        daten = json.loads(request.body)
        fragen = daten.get("fragen", [])
        if not isinstance(fragen, list):
            raise ValueError("fragen muss eine Liste sein")
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"ok": False, "fehler": str(e)}, status=400)

    # IDs normalisieren: pool_<pk>__0, pool_<pk>__1, ...
    for i, f in enumerate(fragen):
        f["id"] = f"pool_{pk}__{i}"
        f.setdefault("typ", "quizfrage")
        f.setdefault("antwort_typ", "single")
        f.setdefault("punkte", 1.0)
        f.setdefault("pflicht", True)

    pool.fragen_json = fragen
    pool.save(update_fields=["fragen_json", "geaendert_am"])
    return JsonResponse({"ok": True, "anzahl": len(fragen)})


@login_required
@require_POST
def pool_aus_portal_importieren(request, pk):
    """
    Fügt Fragen aus einem Portal-Analyse-Ergebnis zum Pool hinzu.
    Body: {analyse_pk: N} oder {fragen: [...]}
    """
    if not _ist_staff(request):
        raise PermissionDenied
    pool = get_object_or_404(QuizFragenPool, pk=pk)
    try:
        daten = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "fehler": "Kein gültiges JSON"}, status=400)

    neue_fragen = []

    # Direkt übergebene Fragen
    if "fragen" in daten:
        neue_fragen = [f for f in daten["fragen"] if f.get("typ") == "quizfrage"]

    # Aus Portal-Analyse laden
    elif "analyse_pk" in daten:
        try:
            from portal.models import FormularAnalyse
            analyse = FormularAnalyse.objects.get(pk=daten["analyse_pk"])
            pfad_data = analyse.ergebnis_json or {}
            for schritt in pfad_data.get("schritte", []):
                for feld in schritt.get("felder_json", []):
                    if feld.get("typ") == "quizfrage":
                        neue_fragen.append(feld)
        except Exception as e:
            return JsonResponse({"ok": False, "fehler": str(e)}, status=400)

    if not neue_fragen:
        return JsonResponse({"ok": False, "fehler": "Keine quizfrage-Felder gefunden."}, status=400)

    # Bestehende Fragen + neue zusammenführen, IDs neu vergeben
    vorhandene = list(pool.fragen_json) if isinstance(pool.fragen_json, list) else []
    alle = vorhandene + neue_fragen
    for i, f in enumerate(alle):
        f["id"] = f"pool_{pk}__{i}"
    pool.fragen_json = alle
    pool.save(update_fields=["fragen_json", "geaendert_am"])

    return JsonResponse({"ok": True, "gesamt": len(alle), "neu": len(neue_fragen)})


@login_required
@require_GET
def pool_als_json(request, pk):
    """Gibt den Pool als JSON zurück (für Editor-Dropdown)."""
    if not _ist_staff(request):
        raise PermissionDenied
    pool = get_object_or_404(QuizFragenPool, pk=pk)
    return JsonResponse({
        "id":          pool.pk,
        "name":        pool.name,
        "anzahl":      pool.anzahl(),
        "fragen":      pool.fragen_json,
    })


@login_required
@require_GET
def pools_json(request):
    """Liste aller Pools als JSON (für Editor-Dropdown)."""
    if not _ist_staff(request):
        return JsonResponse({"pools": []})
    pools = QuizFragenPool.objects.values("id", "name").annotate()
    result = [
        {"id": p["id"], "name": p["name"]}
        for p in QuizFragenPool.objects.all()
    ]
    return JsonResponse({"pools": result})
