# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Dokumente-App Views: Upload, Download, OnlyOffice-Integration."""
import json
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


# ---------------------------------------------------------------------------
# OnlyOffice – Hilfsfunktionen
# ---------------------------------------------------------------------------

# MIME-Typ → OnlyOffice fileType
_MIME_ZU_EXT = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":        "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/msword":                                                         "doc",
    "application/vnd.ms-excel":                                                   "xls",
    "application/vnd.ms-powerpoint":                                              "ppt",
    "application/vnd.oasis.opendocument.text":                                    "odt",
    "application/vnd.oasis.opendocument.spreadsheet":                             "ods",
    "application/vnd.oasis.opendocument.presentation":                            "odp",
    "application/pdf":                                                            "pdf",
}

_ONLYOFFICE_MIME_TYPEN = set(_MIME_ZU_EXT.keys())


def _onlyoffice_jwt(payload: dict) -> str:
    """Signiert den OnlyOffice-Config-Payload als HS256-JWT."""
    import jwt as pyjwt
    secret = getattr(settings, "ONLYOFFICE_JWT_SECRET", "")
    if not secret:
        return ""
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _document_type(file_type: str) -> str:
    """Gibt den OnlyOffice documentType zurueck (word / cell / slide)."""
    if file_type in ("docx", "doc", "odt", "pdf"):
        return "word"
    if file_type in ("xlsx", "xls", "ods"):
        return "cell"
    return "slide"


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
        "onlyoffice_aktiv": bool(getattr(settings, "ONLYOFFICE_URL", "")),
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
        "onlyoffice_aktiv": bool(getattr(settings, "ONLYOFFICE_URL", "")),
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
# OnlyOffice – Editor, Laden, Callback, ForceSave, VersionCheck
# ---------------------------------------------------------------------------


@login_required
def onlyoffice_editor(request, pk):
    """Oeffnet das Dokument im OnlyOffice Document Server.

    Erzeugt eine JWT-signierte Editor-Konfiguration. OnlyOffice laedt das
    Dokument server-seitig ueber onlyoffice_dokument_laden().
    """
    dok = get_object_or_404(Dokument, pk=pk)
    onlyoffice_url = getattr(settings, "ONLYOFFICE_URL", "").rstrip("/")

    if not onlyoffice_url:
        messages.error(request, "OnlyOffice ist nicht konfiguriert (ONLYOFFICE_URL fehlt).")
        return redirect("dokumente:detail", pk=pk)

    if dok.dateityp not in _ONLYOFFICE_MIME_TYPEN:
        messages.error(request, "Dieser Dateityp kann nicht in OnlyOffice bearbeitet werden.")
        return redirect("dokumente:detail", pk=pk)

    # Interne URL fuer OnlyOffice-Server-Callbacks (muss vom Docker-Container erreichbar sein)
    vorgangswerk_base = (
        getattr(settings, "WOPI_BASE_URL", "").rstrip("/")
        or getattr(settings, "VORGANGSWERK_BASE_URL", "").rstrip("/")
    )

    file_type = _MIME_ZU_EXT.get(dok.dateityp, "docx")
    doc_key = f"vorgangswerk-{dok.pk}-v{dok.version}"

    config = {
        "document": {
            "fileType": file_type,
            "key":      doc_key,
            "title":    dok.dateiname,
            "url":      f"{vorgangswerk_base}/dokumente/{dok.pk}/onlyoffice/laden/",
        },
        "documentType": _document_type(file_type),
        "editorConfig": {
            "callbackUrl": f"{vorgangswerk_base}/dokumente/{dok.pk}/onlyoffice/callback/",
            "lang":        "de-DE",
            "mode":        "edit",
            "user": {
                "id":   str(request.user.pk),
                "name": request.user.get_full_name() or request.user.username,
            },
            "customization": {
                "spellcheck": True,
            },
        },
    }
    token = _onlyoffice_jwt(config)

    _protokolliere(dok, ZugriffsProtokoll.AKTION_COLLABORA, request.user, request,
                   "OnlyOffice-Editor geoeffnet")

    return render(request, "dokumente/onlyoffice_editor.html", {
        "dok":            dok,
        "onlyoffice_url": onlyoffice_url,
        "oo_config":      config,
        "token":          token,
    })


def onlyoffice_dokument_laden(request, pk):
    """Liefert den Dokumentinhalt an den OnlyOffice-Server (server-seitig, kein Browser).

    Authentifizierung per JWT-Header (wenn ONLYOFFICE_JWT_SECRET konfiguriert).
    """
    import jwt as pyjwt

    secret = getattr(settings, "ONLYOFFICE_JWT_SECRET", "")
    if secret:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return HttpResponse("Unauthorized", status=401)
        try:
            pyjwt.decode(auth_header[7:], secret, algorithms=["HS256"])
        except pyjwt.PyJWTError:
            return HttpResponse("Unauthorized", status=401)

    dok = get_object_or_404(Dokument, pk=pk)
    return HttpResponse(bytes(dok.inhalt), content_type=dok.dateityp or "application/octet-stream")


@csrf_exempt
def onlyoffice_callback(request, pk):
    """Empfaengt die bearbeitete Datei vom OnlyOffice-Server und speichert sie.

    OnlyOffice sendet status 2 (alle Editoren weg) oder 6 (forcesave).
    """
    import urllib.request as urlreq
    import jwt as pyjwt

    if request.method != "POST":
        return JsonResponse({"error": 0})

    try:
        daten = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": 1})

    # JWT pruefen
    secret = getattr(settings, "ONLYOFFICE_JWT_SECRET", "")
    if secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                pyjwt.decode(auth_header[7:], secret, algorithms=["HS256"])
            except pyjwt.PyJWTError:
                logger.warning("OnlyOffice Callback: ungueltige JWT fuer Dok %s", pk)
                return JsonResponse({"error": 1})

    status = daten.get("status")
    if status not in (2, 6):
        return JsonResponse({"error": 0})

    download_url = daten.get("url")
    if not download_url:
        return JsonResponse({"error": 0})

    # Download-URL von oeffentlicher auf interne OnlyOffice-URL umschreiben
    # (Cloudflare entfernt Auth-Header; interner Weg umgeht das)
    oo_public   = getattr(settings, "ONLYOFFICE_URL", "").rstrip("/")
    oo_internal = getattr(settings, "ONLYOFFICE_INTERNAL_URL", "").rstrip("/")
    if oo_public and oo_internal and download_url.startswith(oo_public):
        download_url = download_url.replace(oo_public, oo_internal, 1)

    dok = get_object_or_404(Dokument, pk=pk)

    try:
        dl_req = urlreq.Request(download_url)
        if secret:
            dl_token = pyjwt.encode({"url": download_url}, secret, algorithm="HS256")
            dl_req.add_header("Authorization", f"Bearer {dl_token}")
        with urlreq.urlopen(dl_req, timeout=30) as resp:
            neuer_inhalt = resp.read()
    except Exception as exc:
        logger.error("OnlyOffice Callback: Download fehlgeschlagen Dok %s: %s", pk, exc)
        return JsonResponse({"error": 1})

    with transaction.atomic():
        DokumentVersion.objects.create(
            dokument=dok,
            version_nr=dok.version,
            inhalt=bytes(dok.inhalt),
            groesse_bytes=dok.groesse_bytes,
            erstellt_von=None,
            kommentar="via OnlyOffice",
        )
        dok.inhalt = neuer_inhalt
        dok.groesse_bytes = len(neuer_inhalt)
        dok.version += 1
        dok.save(update_fields=["inhalt", "groesse_bytes", "version"])
        _protokolliere(dok, ZugriffsProtokoll.AKTION_COLLABORA, None,
                       notiz=f"OnlyOffice v{dok.version}")

    logger.info("OnlyOffice Callback: Dok %s als Version %s gespeichert", pk, dok.version)
    return JsonResponse({"error": 0})


@login_required
@require_POST
def onlyoffice_forcesave(request, pk):
    """Loest einen Force-Save im OnlyOffice Command Service aus.

    Wird vom 'Speichern & zurueck'-Button im Editor aufgerufen.
    """
    import urllib.request as urlreq

    dok = get_object_or_404(Dokument, pk=pk)
    # Interne URL fuer Command Service (nicht durch Cloudflare)
    oo_url = (
        getattr(settings, "ONLYOFFICE_INTERNAL_URL", "").rstrip("/")
        or getattr(settings, "ONLYOFFICE_URL", "").rstrip("/")
    )
    if not oo_url:
        return JsonResponse({"ok": False, "fehler": "OnlyOffice nicht konfiguriert"})

    doc_key = f"vorgangswerk-{dok.pk}-v{dok.version}"
    payload = json.dumps({"c": "forcesave", "key": doc_key}).encode("utf-8")
    req = urlreq.Request(
        f"{oo_url}/coauthoring/CommandService.ashx",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    secret = getattr(settings, "ONLYOFFICE_JWT_SECRET", "")
    if secret:
        import jwt as pyjwt
        token = pyjwt.encode({"c": "forcesave", "key": doc_key}, secret, algorithm="HS256")
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urlreq.urlopen(req, timeout=10) as resp:
            antwort = json.loads(resp.read())
        # error 0 = OK, error 4 = kein aktiver Editor (auch OK)
        if antwort.get("error") in (0, 4):
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "fehler": f"OO Fehler {antwort.get('error')}"})
    except Exception as exc:
        logger.error("ForceSave fehlgeschlagen Dok %s: %s", pk, exc)
        return JsonResponse({"ok": False, "fehler": str(exc)})


@login_required
def onlyoffice_version_check(request, pk):
    """Gibt die aktuelle Versionsnummer des Dokuments zurueck (fuer Polling)."""
    dok = get_object_or_404(Dokument, pk=pk)
    return JsonResponse({"version": dok.version})


# ---------------------------------------------------------------------------
# Audit-Log
# ---------------------------------------------------------------------------


@login_required
def dokument_protokoll(request, pk):
    """Zeigt den vollstaendigen Zugriffsverlauf eines Dokuments."""
    dok = get_object_or_404(Dokument, pk=pk)
    protokolle = dok.protokolle.select_related("user").order_by("-zeitpunkt")
    return render(request, "dokumente/protokoll.html", {"dok": dok, "protokolle": protokolle})
