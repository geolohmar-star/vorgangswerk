# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""DATEV OAuth2 – Connect & Callback Views."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta

from .models import DatevToken
from . import oauth


@login_required
def datev_connect(request):
    """Startet den OAuth2-Flow – leitet zu DATEV-Login weiter."""
    state = oauth.erzeuge_state()
    code_verifier = oauth.erzeuge_code_verifier()
    request.session["datev_state"] = state
    request.session["datev_code_verifier"] = code_verifier
    url = oauth.authorization_url(state, code_verifier)
    return redirect(url)


@login_required
def datev_callback(request):
    """Empfängt Authorization Code, tauscht gegen Token."""
    error = request.GET.get("error")
    if error:
        messages.error(request, f"DATEV-Anmeldung abgebrochen: {error}")
        return redirect("datev:status")

    code = request.GET.get("code", "")
    state = request.GET.get("state", "")

    if state != request.session.pop("datev_state", None):
        messages.error(request, "Ungültiger State-Parameter – bitte erneut versuchen.")
        return redirect("datev:status")

    code_verifier = request.session.pop("datev_code_verifier", "")
    try:
        token_data = oauth.hole_token(code, code_verifier)
    except Exception as exc:
        messages.error(request, f"Token-Austausch fehlgeschlagen: {exc}")
        return redirect("datev:status")

    expires_in = token_data.get("expires_in", 3600)
    expires_at = timezone.now() + timedelta(seconds=int(expires_in))

    DatevToken.objects.update_or_create(
        user=request.user,
        defaults={
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", ""),
            "token_type": token_data.get("token_type", "Bearer"),
            "expires_at": expires_at,
            "scope": token_data.get("scope", ""),
        },
    )
    messages.success(request, "DATEV-Verbindung erfolgreich hergestellt.")
    return redirect("datev:status")


@login_required
def datev_status(request):
    """Übersichtsseite: Verbindungsstatus + Trennen-Button."""
    token = DatevToken.objects.filter(user=request.user).first()
    return render(request, "datev/status.html", {"token": token})


@login_required
def datev_trennen(request):
    """Löscht gespeicherte Tokens (Verbindung trennen)."""
    if request.method == "POST":
        DatevToken.objects.filter(user=request.user).delete()
        messages.success(request, "DATEV-Verbindung getrennt.")
    return redirect("datev:status")


@login_required
def datev_uebertragen(request, sitzung_pk):
    """Überträgt eine abgeschlossene Personalfragebogen-Sitzung nach DATEV."""
    from formulare.models import AntrSitzung
    from django.shortcuts import get_object_or_404
    from .mapping import personalfragebogen_zu_datev
    from . import api as datev_api

    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk, user=request.user)
    token = DatevToken.objects.filter(user=request.user).first()

    if not token:
        messages.error(request, "Keine DATEV-Verbindung vorhanden. Bitte zuerst verbinden.")
        return redirect("datev:status")

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    payload = personalfragebogen_zu_datev(sitzung.gesammelte_daten, token)
    try:
        ergebnis = datev_api.mitarbeiter_erstellen(token, payload)
        employee_id = ergebnis.get("id") or ergebnis.get("employeeId") or ""
        messages.success(
            request,
            f"Mitarbeiter erfolgreich nach DATEV übertragen."
            + (f" (ID: {employee_id})" if employee_id else ""),
        )
    except Exception as exc:
        messages.error(request, f"DATEV-Übertragung fehlgeschlagen: {exc}")

    return redirect("formulare:pfad_abgeschlossen", sitzung_pk=sitzung_pk)


@login_required
@login_required
def datev_lodas_download(request, sitzung_pk):
    """Erzeugt LODAS ASCII-Datei zum Download (ohne API-Upload)."""
    from formulare.models import AntrSitzung
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    from .ascii import erzeuge_lodas_ascii

    from django.conf import settings as _s
    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk)
    token = DatevToken.objects.filter(user=request.user).first()

    beraternummer = (token.consultant_number if token else None) or getattr(_s, "DATEV_BERATERNUMMER", "") or "00000"
    mandantennummer = (token.client_number if token else None) or getattr(_s, "DATEV_MANDANTENNUMMER", "") or "00000"

    daten = sitzung.gesammelte_daten or {}
    inhalt = erzeuge_lodas_ascii(
        daten,
        beraternummer=beraternummer,
        mandantennummer=mandantennummer,
    )
    vorname = daten.get("vorname", "")
    name = daten.get("familienname", "")
    dateiname = f"datev_lodas_{name}_{vorname}_{sitzung.pk}.txt".replace(" ", "_")

    response = HttpResponse(inhalt, content_type="text/plain; charset=cp1252")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


@login_required
@require_POST
def datev_an_steuerberater(request, sitzung_pk):
    """Sendet LODAS-Datei + PDF per E-Mail an den Steuerberater."""
    from formulare.models import AntrSitzung
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.conf import settings as _s
    from django.core.mail import EmailMessage
    from .ascii import erzeuge_lodas_ascii

    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk)
    empfaenger = request.POST.get("steuerberater_email", "").strip() or getattr(_s, "DATEV_STEUERBERATER_EMAIL", "")
    next_url = request.POST.get("next", "/")

    if not empfaenger or "@" not in empfaenger:
        messages.error(request, "Bitte eine gültige E-Mail-Adresse angeben.")
        return redirect(next_url)

    token = DatevToken.objects.filter(user=request.user).first()
    beraternummer = (token.consultant_number if token else None) or getattr(_s, "DATEV_BERATERNUMMER", "") or "00000"
    mandantennummer = (token.client_number if token else None) or getattr(_s, "DATEV_MANDANTENNUMMER", "") or "00000"

    daten = sitzung.gesammelte_daten or {}
    lodas_bytes = erzeuge_lodas_ascii(daten, beraternummer=beraternummer, mandantennummer=mandantennummer)

    vorname = daten.get("vorname", "")
    name = daten.get("familienname", "")
    vgnr = sitzung.vorgangsnummer or f"ANT-{sitzung.pk:05d}"
    dateiname_lodas = f"datev_lodas_{name}_{vorname}.txt".replace(" ", "_")
    dateiname_pdf = f"personalfragebogen_{name}_{vorname}.pdf".replace(" ", "_")

    betreff = f"Personalfragebogen {name}, {vorname} – {vgnr}"
    text = (
        f"Guten Tag,\n\n"
        f"anbei erhalten Sie die Unterlagen für den neuen Mitarbeiter:\n\n"
        f"  Name:            {vorname} {name}\n"
        f"  Vorgangsnummer:  {vgnr}\n\n"
        f"Im Anhang:\n"
        f"  1. Ausgefüllter Personalfragebogen (PDF)\n"
        f"  2. DATEV LODAS ASCII-Importdatei\n\n"
        f"Mit freundlichen Grüßen\n{request.user.get_full_name() or request.user.username}"
    )

    try:
        mail = EmailMessage(subject=betreff, body=text, to=[empfaenger])
        mail.attach(dateiname_lodas, lodas_bytes, "text/plain")

        # PDF erzeugen
        try:
            from formulare.views import _erzeuge_ausgefuelltes_pdf_bytes
            pdf_bytes = _erzeuge_ausgefuelltes_pdf_bytes(sitzung)
            if pdf_bytes:
                mail.attach(dateiname_pdf, pdf_bytes, "application/pdf")
        except Exception:
            pass

        mail.send(fail_silently=False)
        messages.success(request, f"Unterlagen wurden an {empfaenger} gesendet.")
    except Exception as exc:
        messages.error(request, f"Fehler beim Senden: {exc}")

    return redirect(next_url)


@login_required
def datev_lodas_hochladen(request, sitzung_pk):
    """Erzeugt LODAS ASCII-Datei und lädt sie direkt per HR:Files API hoch."""
    from formulare.models import AntrSitzung
    from django.shortcuts import get_object_or_404
    from .ascii import erzeuge_lodas_ascii
    from . import api as datev_api

    sitzung = get_object_or_404(AntrSitzung, pk=sitzung_pk, user=request.user)
    token = DatevToken.objects.filter(user=request.user).first()

    if not token:
        messages.error(request, "Keine DATEV-Verbindung vorhanden.")
        return redirect("datev:status")

    if request.method != "POST":
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(["POST"])

    inhalt = erzeuge_lodas_ascii(
        sitzung.gesammelte_daten,
        beraternummer=token.consultant_number,
        mandantennummer=token.client_number,
    )
    vorname = sitzung.gesammelte_daten.get("vorname", "")
    name = sitzung.gesammelte_daten.get("familienname", "")
    dateiname = f"datev_lodas_{name}_{vorname}_{sitzung.pk}.txt".replace(" ", "_")

    try:
        datev_api.datei_hochladen(token, inhalt, dateiname)
        messages.success(request, "LODAS-Datei erfolgreich an DATEV übermittelt.")
    except Exception as exc:
        messages.error(request, f"HR:Files Upload fehlgeschlagen: {exc}")

    return redirect("formulare:pfad_abgeschlossen", sitzung_pk=sitzung_pk)
