# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Dokumente-App Views: Upload, Download, WOPI-Protokoll fuer Collabora Online."""
import logging
import mimetypes

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import DokumentBearbeitenForm, DokumentHochladenForm
from .models import Dokument, DokumentKategorie, DokumentVersion, ZugriffsProtokoll

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------


def _protokolliere(dokument, aktion, user, request=None, notiz=""):
    """Erzeugt einen ZugriffsProtokoll-Eintrag."""
    ip = None
    if request:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")
    ZugriffsProtokoll.objects.create(
        dokument=dokument,
        dokument_titel=dokument.titel if dokument else "?",
        aktion=aktion,
        user=user,
        ip_adresse=ip,
        notiz=notiz,
    )


def _get_collabora_url():
    return getattr(settings, "COLLABORA_URL", "").rstrip("/")


# ---------------------------------------------------------------------------
# Dokumentliste & Suche
# ---------------------------------------------------------------------------


@login_required
def dokument_liste(request):
    """Liste aller Dokumente mit Suche und Kategorie-Filter."""
    qs = Dokument.objects.select_related("kategorie", "erstellt_von")

    suche = request.GET.get("q", "").strip()
    if suche:
        qs = qs.filter(titel__icontains=suche) | Dokument.objects.filter(
            dateiname__icontains=suche
        )

    kategorie_id = request.GET.get("kategorie")
    if kategorie_id:
        qs = qs.filter(kategorie_id=kategorie_id)

    kategorien = DokumentKategorie.objects.filter(elternkategorie__isnull=True).prefetch_related(
        "unterkategorien"
    )
    dokumente = qs.order_by("-geaendert_am")

    kontext = {
        "dokumente": dokumente,
        "kategorien": kategorien,
        "suche": suche,
        "aktive_kategorie": kategorie_id,
        "collabora_aktiv": bool(_get_collabora_url()),
    }
    return render(request, "dokumente/liste.html", kontext)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@login_required
def dokument_hochladen(request):
    """Dokument hochladen."""
    form = DokumentHochladenForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        datei = request.FILES["datei"]
        inhalt = datei.read()
        mime = (
            datei.content_type
            or mimetypes.guess_type(datei.name)[0]
            or "application/octet-stream"
        )

        with transaction.atomic():
            dok = Dokument.objects.create(
                titel=form.cleaned_data["titel"] or datei.name,
                dateiname=datei.name,
                dateityp=mime,
                inhalt=inhalt,
                groesse_bytes=len(inhalt),
                kategorie=form.cleaned_data.get("kategorie"),
                erstellt_von=request.user,
                version=1,
            )
            if form.cleaned_data.get("tags"):
                dok.tags.set(form.cleaned_data["tags"])
            _protokolliere(dok, ZugriffsProtokoll.AKTION_UPLOAD, request.user, request)

        messages.success(request, f"'{dok.titel}' wurde hochgeladen.")
        return redirect("dokumente:detail", pk=dok.pk)

    return render(request, "dokumente/hochladen.html", {"form": form})


# ---------------------------------------------------------------------------
# Detail & Download
# ---------------------------------------------------------------------------


@login_required
def dokument_detail(request, pk):
    """Detail-Ansicht eines Dokuments."""
    dok = get_object_or_404(
        Dokument.objects.select_related("kategorie", "erstellt_von").prefetch_related("tags"),
        pk=pk,
    )
    versionen = dok.versionen.select_related("erstellt_von").order_by("-version_nr")[:10]
    protokolle = dok.protokolle.select_related("user").order_by("-zeitpunkt")[:20]

    kontext = {
        "dok": dok,
        "versionen": versionen,
        "protokolle": protokolle,
        "collabora_aktiv": bool(_get_collabora_url()),
    }
    return render(request, "dokumente/detail.html", kontext)


@login_required
def dokument_download(request, pk):
    """Laedt das Dokument als Datei herunter."""
    dok = get_object_or_404(Dokument, pk=pk)
    _protokolliere(dok, ZugriffsProtokoll.AKTION_DOWNLOAD, request.user, request)
    response = HttpResponse(
        bytes(dok.inhalt),
        content_type=dok.dateityp or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{dok.dateiname}"'
    return response


@login_required
def dokument_vorschau(request, pk):
    """Zeigt das Dokument inline im Browser (PDF und Bilder)."""
    dok = get_object_or_404(Dokument, pk=pk)
    _protokolliere(dok, ZugriffsProtokoll.AKTION_VORSCHAU, request.user, request)
    response = HttpResponse(
        bytes(dok.inhalt),
        content_type=dok.dateityp or "application/octet-stream",
    )
    response["Content-Disposition"] = f'inline; filename="{dok.dateiname}"'
    return response


# ---------------------------------------------------------------------------
# Bearbeiten (Metadaten)
# ---------------------------------------------------------------------------


@login_required
def dokument_bearbeiten(request, pk):
    """Metadaten eines Dokuments bearbeiten."""
    dok = get_object_or_404(Dokument, pk=pk)
    form = DokumentBearbeitenForm(request.POST or None, instance=dok)
    if request.method == "POST" and form.is_valid():
        form.save()
        _protokolliere(
            dok, ZugriffsProtokoll.AKTION_GEAENDERT, request.user, request,
            "Metadaten geaendert",
        )
        messages.success(request, "Dokument wurde gespeichert.")
        return redirect("dokumente:detail", pk=dok.pk)

    return render(request, "dokumente/bearbeiten.html", {"form": form, "dok": dok})


# ---------------------------------------------------------------------------
# Neue Version hochladen
# ---------------------------------------------------------------------------


@login_required
@require_POST
def dokument_version_hochladen(request, pk):
    """Laedt eine neue Version eines bestehenden Dokuments hoch."""
    dok = get_object_or_404(Dokument, pk=pk)
    datei = request.FILES.get("datei")
    if not datei:
        messages.error(request, "Keine Datei ausgewaehlt.")
        return redirect("dokumente:detail", pk=dok.pk)

    inhalt = datei.read()
    kommentar = request.POST.get("kommentar", "")

    with transaction.atomic():
        DokumentVersion.objects.create(
            dokument=dok,
            version_nr=dok.version,
            inhalt=bytes(dok.inhalt),
            groesse_bytes=dok.groesse_bytes,
            erstellt_von=request.user,
            kommentar=f"Vor Upload v{dok.version + 1}",
        )
        dok.inhalt = inhalt
        dok.groesse_bytes = len(inhalt)
        dok.dateiname = datei.name
        dok.dateityp = (
            datei.content_type
            or mimetypes.guess_type(datei.name)[0]
            or dok.dateityp
        )
        dok.version += 1
        dok.save(update_fields=["inhalt", "groesse_bytes", "dateiname", "dateityp", "version"])
        _protokolliere(
            dok, ZugriffsProtokoll.AKTION_UPLOAD, request.user, request,
            f"Neue Version {dok.version}. {kommentar}",
        )

    messages.success(request, f"Version {dok.version} wurde hochgeladen.")
    return redirect("dokumente:detail", pk=dok.pk)


@login_required
@require_POST
def dokument_version_wiederherstellen(request, pk, version_nr):
    """Stellt eine archivierte Version wieder her."""
    dok = get_object_or_404(Dokument, pk=pk)
    alte_version = get_object_or_404(DokumentVersion, dokument=dok, version_nr=version_nr)

    with transaction.atomic():
        DokumentVersion.objects.get_or_create(
            dokument=dok,
            version_nr=dok.version,
            defaults={
                "inhalt": bytes(dok.inhalt),
                "groesse_bytes": dok.groesse_bytes,
                "erstellt_von": request.user,
                "kommentar": "Vor Wiederherstellung",
            },
        )
        dok.inhalt = bytes(alte_version.inhalt)
        dok.groesse_bytes = alte_version.groesse_bytes
        dok.version += 1
        dok.save(update_fields=["inhalt", "groesse_bytes", "version"])
        _protokolliere(
            dok, ZugriffsProtokoll.AKTION_VERSION, request.user, request,
            f"Version {version_nr} wiederhergestellt",
        )

    messages.success(request, f"Version {version_nr} wurde wiederhergestellt.")
    return redirect("dokumente:detail", pk=dok.pk)


# ---------------------------------------------------------------------------
# Loeschen
# ---------------------------------------------------------------------------


@login_required
@require_POST
def dokument_loeschen(request, pk):
    """Loescht ein Dokument (nur Staff)."""
    if not request.user.is_staff:
        messages.error(request, "Keine Berechtigung.")
        return redirect("dokumente:liste")

    dok = get_object_or_404(Dokument, pk=pk)
    titel = dok.titel
    _protokolliere(dok, ZugriffsProtokoll.AKTION_GELOESCHT, request.user, request)
    dok.delete()
    messages.success(request, f"'{titel}' wurde geloescht.")
    return redirect("dokumente:liste")


# ---------------------------------------------------------------------------
# Collabora WOPI – Editor oeffnen
# ---------------------------------------------------------------------------


@login_required
def collabora_editor(request, pk):
    """Oeffnet das Dokument im Collabora Online Editor (WOPI).

    Erzeugt einen frischen WOPI-Token und liefert die Editor-Seite.
    """
    dok = get_object_or_404(Dokument, pk=pk)
    collabora_url = _get_collabora_url()

    if not collabora_url:
        messages.error(request, "Collabora Online ist nicht konfiguriert (COLLABORA_URL fehlt).")
        return redirect("dokumente:detail", pk=pk)

    if not dok.ist_office_dokument:
        messages.error(request, "Dieser Dateityp kann nicht in Collabora bearbeitet werden.")
        return redirect("dokumente:detail", pk=pk)

    token = dok.erstelle_wopi_token()

    base_url = getattr(
        settings, "VORGANGSWERK_BASE_URL",
        request.build_absolute_uri("/").rstrip("/"),
    )
    wopi_src = f"{base_url}/dokumente/wopi/files/{dok.pk}/"

    kontext = {
        "dok": dok,
        "collabora_url": collabora_url,
        "wopi_src": wopi_src,
        "wopi_token": token,
    }
    return render(request, "dokumente/collabora_editor.html", kontext)


# ---------------------------------------------------------------------------
# WOPI-Protokoll (fuer Collabora Online)
# ---------------------------------------------------------------------------


@csrf_exempt
def wopi_files_dispatch(request, pk):
    """WOPI CheckFileInfo – GET /dokumente/wopi/files/{pk}/"""
    token = request.GET.get("access_token", "")
    dok = get_object_or_404(Dokument, pk=pk)

    if not dok.wopi_token or dok.wopi_token != token or not dok.wopi_token_gueltig():
        return HttpResponse("Unauthorized", status=401)

    user_id = ""
    user_name = "Unbekannt"
    if request.user.is_authenticated:
        user_id = str(request.user.pk)
        user_name = request.user.get_full_name() or request.user.username

    info = {
        "BaseFileName": dok.dateiname,
        "Size": dok.groesse_bytes,
        "Version": str(dok.version),
        "OwnerId": str(dok.erstellt_von_id or ""),
        "UserId": user_id,
        "UserFriendlyName": user_name,
        "UserCanWrite": True,
        "UserCanRename": False,
        "SupportsUpdate": True,
        "SupportsLocks": False,
        "SupportsGetLock": False,
        "LastModifiedTime": dok.geaendert_am.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return JsonResponse(info)


@csrf_exempt
def wopi_contents_dispatch(request, pk):
    """WOPI GetFile/PutFile – /dokumente/wopi/files/{pk}/contents/

    GET → liefert Dateiinhalt
    POST → speichert bearbeiteten Inhalt
    """
    token = request.GET.get("access_token", "")
    dok = get_object_or_404(Dokument, pk=pk)

    if not dok.wopi_token or dok.wopi_token != token or not dok.wopi_token_gueltig():
        return HttpResponse("Unauthorized", status=401)

    if request.method == "GET":
        # GetFile
        response = HttpResponse(bytes(dok.inhalt), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{dok.dateiname}"'
        return response

    elif request.method == "POST":
        # PutFile – Collabora speichert den bearbeiteten Inhalt
        inhalt = request.body
        if not inhalt:
            return JsonResponse({"LastModifiedTime": dok.geaendert_am.strftime("%Y-%m-%dT%H:%M:%SZ")})

        with transaction.atomic():
            DokumentVersion.objects.create(
                dokument=dok,
                version_nr=dok.version,
                inhalt=bytes(dok.inhalt),
                groesse_bytes=dok.groesse_bytes,
                erstellt_von=None,
                kommentar="Vor Collabora-Speicherung",
            )
            dok.inhalt = inhalt
            dok.groesse_bytes = len(inhalt)
            dok.version += 1
            dok.save(update_fields=["inhalt", "groesse_bytes", "version"])
            # Protokoll mit Dokument-Ersteller als Naehrungswert
            _protokolliere(
                dok, ZugriffsProtokoll.AKTION_COLLABORA, dok.erstellt_von,
                notiz=f"Collabora v{dok.version}",
            )

        return JsonResponse({
            "LastModifiedTime": dok.geaendert_am.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    return HttpResponse("Method Not Allowed", status=405)


# ---------------------------------------------------------------------------
# Audit-Log
# ---------------------------------------------------------------------------


@login_required
def dokument_protokoll(request, pk):
    """Zeigt den vollstaendigen Zugriffsverlauf eines Dokuments."""
    dok = get_object_or_404(Dokument, pk=pk)
    protokolle = dok.protokolle.select_related("user").order_by("-zeitpunkt")
    return render(request, "dokumente/protokoll.html", {"dok": dok, "protokolle": protokolle})
