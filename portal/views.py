# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Portal-Views: Registrierung, Dashboard, PDF-Upload, Stripe-Checkout.
"""
import datetime
import json
import logging
import threading
import re

from django.db.models import Count

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import PortalAccount, FormularAnalyse, CreditTransaktion, Einladung, CREDIT_PAKETE, CREDIT_PAKETE_BY_ID
from .services import analysiere_formular, importiere_pfad_aus_analyse

logger = logging.getLogger("vorgangswerk.portal")

MAX_PDF_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_PENDING = 5  # Max gleichzeitige Analysen pro Konto


# ---------------------------------------------------------------------------
# Dekoratoren
# ---------------------------------------------------------------------------

def portal_login_required(view_func):
    """Leitet auf /portal/login/ um wenn nicht eingeloggt oder kein PortalAccount."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('portal:login')}?next={request.path}")
        try:
            _ = request.user.portal_account
        except PortalAccount.DoesNotExist:
            logout(request)
            return redirect(reverse("portal:login"))
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def registrierung(request, token):
    """Einladungsbasierte Registrierung — nur mit gültigem Token."""
    try:
        einladung = Einladung.objects.get(token=token)
    except Einladung.DoesNotExist:
        return render(request, "portal/registrierung_ungueltig.html", {
            "grund": "Dieser Einladungslink ist ungültig."
        })

    if not einladung.ist_gueltig():
        return render(request, "portal/registrierung_ungueltig.html", {
            "grund": "Dieser Einladungslink wurde bereits verwendet oder ist abgelaufen."
        })

    if request.method == "POST":
        passwort1 = request.POST.get("passwort1", "")
        passwort2 = request.POST.get("passwort2", "")

        fehler = []
        if passwort1 != passwort2:
            fehler.append("Die Passwörter stimmen nicht überein.")
        if len(passwort1) < 12:
            fehler.append("Das Passwort muss mindestens 12 Zeichen lang sein.")
        if User.objects.filter(username=einladung.email).exists():
            fehler.append("Diese E-Mail-Adresse ist bereits registriert.")

        if fehler:
            return render(request, "portal/registrierung.html", {
                "fehler": fehler, "einladung": einladung
            })

        from django.utils import timezone as tz
        user = User.objects.create_user(
            username=einladung.email,
            email=einladung.email,
            password=passwort1,
            is_staff=False,
            is_superuser=False,
        )
        account = PortalAccount.objects.create(
            user=user,
            credits=einladung.start_credits,
            email_verifiziert=True,
        )
        einladung.eingeloest_am = tz.now()
        einladung.eingeloest_von = user
        einladung.save(update_fields=["eingeloest_am", "eingeloest_von"])

        if einladung.start_credits > 0:
            from .models import CreditTransaktion
            CreditTransaktion.objects.create(
                account=account,
                typ="kauf",
                betrag=einladung.start_credits,
                beschreibung="Start-Credits aus Einladung",
            )

        messages.success(request, f"Willkommen! Dein Konto wurde erstellt{' mit ' + str(einladung.start_credits) + ' Start-Credits' if einladung.start_credits else ''}.")
        user_obj = authenticate(request, username=einladung.email, password=passwort1)
        if user_obj:
            login(request, user_obj)
            return redirect(reverse("portal:dashboard"))
        return redirect(reverse("portal:login"))

    return render(request, "portal/registrierung.html", {"einladung": einladung})


def _sende_verifikationsmail(request, email: str, token: str):
    """Sendet Verifizierungsmail."""
    verifizier_url = request.build_absolute_uri(
        reverse("portal:email_verifizieren", args=[token])
    )
    try:
        send_mail(
            subject="Vorgangswerk Portal – E-Mail bestätigen",
            message=(
                f"Hallo,\n\nbitte bestätige deine E-Mail-Adresse:\n\n{verifizier_url}\n\n"
                "Dieser Link ist 48 Stunden gültig.\n\nVorgangswerk"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception as e:
        logger.warning("Verifizierungsmail konnte nicht gesendet werden: %s", e)


def email_verifizieren(request, token):
    try:
        account = PortalAccount.objects.get(verifikations_token=token)
        account.email_verifiziert = True
        account.verifikations_token = ""
        account.save(update_fields=["email_verifiziert", "verifikations_token"])
        messages.success(request, "E-Mail erfolgreich bestätigt! Du kannst dich jetzt anmelden.")
    except PortalAccount.DoesNotExist:
        messages.error(request, "Ungültiger oder abgelaufener Verifizierungslink.")
    return redirect(reverse("portal:login"))


def portal_login(request):
    if request.user.is_authenticated and hasattr(request.user, "portal_account"):
        return redirect(reverse("portal:dashboard"))

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        passwort = request.POST.get("passwort", "")

        user = authenticate(request, username=email, password=passwort)
        if user is None:
            return render(request, "portal/login.html", {
                "fehler": "E-Mail oder Passwort falsch.",
                "email": email,
            })

        if not hasattr(user, "portal_account"):
            return render(request, "portal/login.html", {
                "fehler": "Dieses Konto hat keinen Portal-Zugang.",
                "email": email,
            })

        login(request, user)
        next_url = request.GET.get("next", reverse("portal:dashboard"))
        return redirect(next_url)

    return render(request, "portal/login.html", {})


def portal_logout(request):
    logout(request)
    return redirect(reverse("portal:login"))


# ---------------------------------------------------------------------------
# Admin-Verwaltung (nur Staff)
# ---------------------------------------------------------------------------

@login_required
def admin_verwaltung(request):
    """Verwaltungsoberfläche für Einladungen und Portal-Nutzer (nur Staff)."""
    if not request.user.is_staff:
        messages.error(request, "Kein Zugriff.")
        return redirect(reverse("portal:login"))

    from django.utils import timezone as tz

    fehler = None
    erfolg = None

    if request.method == "POST":
        aktion = request.POST.get("aktion")

        if aktion == "einladung_erstellen":
            email = request.POST.get("email", "").strip().lower()
            start_credits = int(request.POST.get("start_credits", 0) or 0)
            gueltig_tage = int(request.POST.get("gueltig_tage", 0) or 0)
            notiz = request.POST.get("notiz", "").strip()

            if not email or "@" not in email:
                fehler = "Bitte eine gültige E-Mail-Adresse eingeben."
            elif Einladung.objects.filter(email=email).exists():
                fehler = f"Eine Einladung für {email} existiert bereits."
            else:
                gueltig_bis = tz.now() + datetime.timedelta(days=gueltig_tage) if gueltig_tage else None
                einladung = Einladung.objects.create(
                    email=email,
                    start_credits=start_credits,
                    gueltig_bis=gueltig_bis,
                    notiz=notiz,
                )
                erfolg = f"Einladung für {email} erstellt."
                # Sofort E-Mail senden wenn gewünscht
                if request.POST.get("sofort_senden"):
                    _sende_einladungsmail(request, einladung)
                    erfolg += " E-Mail wurde verschickt."

        elif aktion == "einladung_senden":
            pk = request.POST.get("pk")
            try:
                einladung = Einladung.objects.get(pk=pk)
                _sende_einladungsmail(request, einladung)
                erfolg = f"Einladungs-E-Mail an {einladung.email} gesendet."
            except Einladung.DoesNotExist:
                fehler = "Einladung nicht gefunden."

        elif aktion == "einladung_loeschen":
            pk = request.POST.get("pk")
            try:
                einladung = Einladung.objects.get(pk=pk, eingeloest_am__isnull=True)
                email = einladung.email
                einladung.delete()
                erfolg = f"Einladung für {email} gelöscht."
            except Einladung.DoesNotExist:
                fehler = "Einladung nicht gefunden oder bereits eingelöst."

        elif aktion == "credits_anpassen":
            account_pk = request.POST.get("account_pk")
            betrag = int(request.POST.get("betrag", 0) or 0)
            beschreibung = request.POST.get("beschreibung", "Manuelle Anpassung").strip()
            try:
                account = PortalAccount.objects.get(pk=account_pk)
                account.credits = max(0, account.credits + betrag)
                account.save(update_fields=["credits"])
                CreditTransaktion.objects.create(
                    account=account,
                    typ="kauf" if betrag > 0 else "rueckerstattung",
                    betrag=betrag,
                    beschreibung=beschreibung,
                )
                erfolg = f"Credits für {account.user.email} angepasst ({betrag:+d})."
            except PortalAccount.DoesNotExist:
                fehler = "Konto nicht gefunden."

        return redirect(reverse("portal:admin_verwaltung") + (f"?erfolg={erfolg}" if erfolg else f"?fehler={fehler}"))

    einladungen = Einladung.objects.select_related("eingeloest_von").order_by("-erstellt_am")
    nutzer = PortalAccount.objects.select_related("user").annotate(
        analyse_anzahl=Count("analysen")
    ).order_by("-erstellt_am")

    return render(request, "portal/admin_verwaltung.html", {
        "einladungen": einladungen,
        "nutzer": nutzer,
        "erfolg": request.GET.get("erfolg"),
        "fehler": request.GET.get("fehler"),
        "jetzt": tz.now(),
    })


def _sende_einladungsmail(request, einladung):
    link = request.build_absolute_uri(
        reverse("portal:registrierung", args=[einladung.token])
    )
    try:
        send_mail(
            subject="Einladung zum Vorgangswerk Portal",
            message=(
                f"Hallo,\n\n"
                f"du wurdest eingeladen, das Vorgangswerk Portal zu nutzen.\n\n"
                f"Registriere dich hier:\n{link}\n\n"
                + (f"Dein Konto wird mit {einladung.start_credits} Start-Credits ausgestattet.\n\n" if einladung.start_credits else "")
                + "Vorgangswerk"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[einladung.email],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("Einladungsmail fehlgeschlagen: %s", e)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@portal_login_required
def dashboard(request):
    account = request.user.portal_account
    analysen = account.analysen.all()[:20]
    transaktionen = account.transaktionen.all()[:10]
    return render(request, "portal/dashboard.html", {
        "account": account,
        "analysen": analysen,
        "transaktionen": transaktionen,
    })


# ---------------------------------------------------------------------------
# PDF-Upload & Analyse
# ---------------------------------------------------------------------------

@portal_login_required
def upload(request):
    account = request.user.portal_account

    if request.method == "POST":
        # Credits prüfen
        if account.credits < 1:
            messages.error(request, "Nicht genug Credits. Bitte kaufe erst neue Credits.")
            return redirect(reverse("portal:credits_kaufen"))

        # Datei prüfen
        datei = request.FILES.get("pdf_datei")
        if not datei:
            messages.error(request, "Bitte wähle eine PDF-Datei aus.")
            return redirect(reverse("portal:upload"))

        if not datei.name.lower().endswith(".pdf"):
            messages.error(request, "Nur PDF-Dateien werden akzeptiert.")
            return redirect(reverse("portal:upload"))

        if datei.size > MAX_PDF_BYTES:
            messages.error(request, f"Die Datei ist zu groß (max. {MAX_PDF_BYTES // (1024*1024)} MB).")
            return redirect(reverse("portal:upload"))

        # Offene Jobs prüfen
        pending = account.analysen.filter(
            status__in=[FormularAnalyse.STATUS_WARTEND, FormularAnalyse.STATUS_VERARBEITUNG]
        ).count()
        if pending >= MAX_PENDING:
            messages.error(request, f"Zu viele laufende Analysen (max. {MAX_PENDING}). Warte auf Abschluss.")
            return redirect(reverse("portal:dashboard"))

        # Magic-Bytes prüfen (PDF beginnt mit %PDF)
        pdf_bytes = datei.read()
        if not pdf_bytes.startswith(b"%PDF"):
            messages.error(request, "Die Datei ist kein gültiges PDF.")
            return redirect(reverse("portal:upload"))

        # Optional: Original-PDF (ohne Marker)
        original_bytes = None
        datei_original = request.FILES.get("pdf_original")
        if datei_original:
            if not datei_original.name.lower().endswith(".pdf"):
                messages.error(request, "Original-PDF: nur PDF-Dateien werden akzeptiert.")
                return redirect(reverse("portal:upload"))
            original_bytes = datei_original.read()
            if not original_bytes.startswith(b"%PDF"):
                messages.error(request, "Original-PDF ist kein gültiges PDF.")
                return redirect(reverse("portal:upload"))

        # Credit abziehen
        if not account.credit_abziehen(1, f"Analyse: {datei.name[:80]}"):
            messages.error(request, "Nicht genug Credits.")
            return redirect(reverse("portal:credits_kaufen"))

        # Analyse-Job erstellen
        analyse = FormularAnalyse.objects.create(
            account=account,
            dateiname=datei.name[:255],
            pdf_inhalt=pdf_bytes,
            pdf_original=original_bytes,
            status=FormularAnalyse.STATUS_WARTEND,
            credits_verbraucht=1,
        )

        # Analyse in separatem Thread starten
        t = threading.Thread(target=analysiere_formular, args=(analyse.pk,), daemon=True)
        t.start()

        return redirect(reverse("portal:analyse_detail", args=[analyse.pk]))

    return render(request, "portal/upload.html", {
        "account": account,
        "bentopdf_url": getattr(settings, "BENTOPDF_URL", ""),
    })


@portal_login_required
def analyse_detail(request, pk):
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)
    bentopdf_url = getattr(settings, "BENTOPDF_URL", "")
    pdf_url = ""
    if bentopdf_url:
        pdf_url = request.build_absolute_uri(
            reverse("portal:analyse_pdf", args=[pk])
        )
    return render(request, "portal/analyse_detail.html", {
        "account": account,
        "analyse": analyse,
        "bentopdf_url": bentopdf_url,
        "pdf_url": pdf_url,
    })


@portal_login_required
@require_GET
def analyse_pdf(request, pk):
    """Liefert die gespeicherte PDF-Datei der Analyse."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)
    pdf_bytes = bytes(analyse.pdf_inhalt)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{analyse.dateiname}"'
    return response


@portal_login_required
def analyse_original_pdf_upload(request, pk):
    """Nimmt das saubere Original-PDF (ohne Marker) entgegen und speichert es."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    if request.method != "POST":
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    datei = request.FILES.get("pdf_original")
    if not datei:
        messages.error(request, "Bitte wähle eine PDF-Datei aus.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    if not datei.name.lower().endswith(".pdf"):
        messages.error(request, "Nur PDF-Dateien werden akzeptiert.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    pdf_bytes = datei.read()
    if not pdf_bytes.startswith(b"%PDF"):
        messages.error(request, "Die Datei ist kein gültiges PDF.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    analyse.pdf_original = pdf_bytes
    analyse.save(update_fields=["pdf_original"])
    messages.success(request, "Original-PDF gespeichert. Es wird beim Befüllen verwendet.")
    return redirect(reverse("portal:analyse_detail", args=[pk]))


@portal_login_required
@require_GET
def analyse_diagnose_pdf(request, pk):
    """Befüllt das Original-PDF mit den AcroForm-Feldnamen als Werte (Diagnose-Werkzeug).
    So sieht man visuell welcher interne Feldname welchem Formularfeld entspricht."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    try:
        import io
        from pypdf import PdfReader, PdfWriter
        pdf_bytes = bytes(analyse.pdf_inhalt)
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        writer.append(reader)

        # Alle AcroForm-Feldnamen sammeln
        field_map = {}
        for felder in (reader.get_form_text_fields() or {}).keys():
            field_map[felder] = felder  # Name als Wert eintragen

        for page in writer.pages:
            try:
                writer.update_page_form_field_values(page, field_map)
            except Exception:
                pass

        buf = io.BytesIO()
        writer.write(buf)
        pdf_out = buf.getvalue()
    except Exception as exc:
        logger.error("Diagnose-PDF Fehler: %s", exc)
        messages.error(request, f"Diagnose-PDF fehlgeschlagen: {exc}")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    dateiname = f"diagnose_{analyse.dateiname}"
    response = HttpResponse(pdf_out, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{dateiname}"'
    return response


@portal_login_required
@require_GET
def analyse_seite_png(request, pk, seite_nr):
    """Rendert Seite N des Analyse-PDFs als PNG (für den interaktiven Viewer)."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)
    try:
        from pdf2image import convert_from_bytes
        import io as _io
        pages = convert_from_bytes(
            bytes(analyse.pdf_inhalt), dpi=120,
            first_page=seite_nr, last_page=seite_nr,
        )
        if not pages:
            return HttpResponse(status=404)
        buf = _io.BytesIO()
        pages[0].save(buf, format="PNG")
        response = HttpResponse(buf.getvalue(), content_type="image/png")
        response["Cache-Control"] = "private, max-age=3600"
        return response
    except Exception as exc:
        logger.error("Seiten-Render Fehler (Analyse %d Seite %d): %s", pk, seite_nr, exc)
        return HttpResponse(status=500)


@portal_login_required
@require_GET
def analyse_felder_json(request, pk):
    """Gibt AcroForm-Feldnamen + Positionen (Seite, Rect) als JSON zurück."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)
    try:
        import io as _io
        import pypdf
        reader = pypdf.PdfReader(_io.BytesIO(bytes(analyse.pdf_inhalt)))
        seiten = []
        felder = []
        def _resolve_name(widget_obj):
            """Löst den vollständigen Feldnamen auf, auch bei Parent-Hierarchie."""
            teile = []
            obj = widget_obj
            for _ in range(6):  # max 6 Ebenen tief
                t = obj.get("/T")
                if t:
                    teile.append(str(t).strip())
                parent_ref = obj.get("/Parent")
                if not parent_ref:
                    break
                try:
                    obj = parent_ref.get_object()
                except Exception:
                    break
            if not teile:
                return ""
            # Letztes Element = eigener Name, davor = Parent-Namen → zusammenbauen
            teile.reverse()
            # Nur den Blatt-Namen zurückgeben (kein vollständiger Pfad nötig)
            return teile[-1]

        # Seiten-Dimensionen + Seiten-Index für Feldbaum-Durchlauf
        seiten_index: dict[int, int] = {}  # pypdf page object id → seite_nr (0-based)
        for seite_nr, seite in enumerate(reader.pages):
            seiten.append({
                "breite": float(seite.mediabox.width),
                "hoehe": float(seite.mediabox.height),
            })

        # Hilfsfunktion: Seite eines Widgets über /P ermitteln
        def _seite_von(widget_obj) -> int:
            p = widget_obj.get("/P")
            if p:
                try:
                    page_obj = p.get_object()
                    for i, pg in enumerate(reader.pages):
                        if pg.indirect_reference == page_obj.indirect_reference:
                            return i
                except Exception:
                    pass
            return 0

        # Erster Durchlauf: Seiten-/Annots (Standard-Weg)
        gefunden: set[tuple] = set()  # (name, seite_nr) um Duplikate zu vermeiden

        for seite_nr, seite in enumerate(reader.pages):
            for ref in (seite.get("/Annots") or []):
                try:
                    a = ref.get_object()
                    if a.get("/Subtype") != "/Widget":
                        continue
                    name = _resolve_name(a)
                    if not name:
                        continue
                    rect = a.get("/Rect", [0, 0, 0, 0])
                    rx1, ry1, rx2, ry2 = [float(v) for v in rect]
                    # Normalisieren: einige PDFs haben y1 > y2 (invertierte Rects)
                    x1, x2 = min(rx1, rx2), max(rx1, rx2)
                    y1, y2 = min(ry1, ry2), max(ry1, ry2)
                    key = (name, seite_nr)
                    if key not in gefunden:
                        gefunden.add(key)
                        felder.append({
                            "name": name,
                            "seite": seite_nr + 1,
                            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        })
                except Exception:
                    pass

        # Zweiter Durchlauf: AcroForm-Feldbaum direkt (findet Felder ohne Seiten-Annot-Eintrag)
        def _walk_felder(nodes):
            for ref in (nodes or []):
                try:
                    obj = ref.get_object()
                except Exception:
                    continue
                kids = obj.get("/Kids")
                if kids:
                    _walk_felder(kids)
                # Widget mit eigenem /Rect?
                if obj.get("/Subtype") == "/Widget" or obj.get("/Rect"):
                    name = _resolve_name(obj)
                    rect = obj.get("/Rect")
                    if name and rect:
                        try:
                            rx1, ry1, rx2, ry2 = [float(v) for v in rect]
                            x1, x2 = min(rx1, rx2), max(rx1, rx2)
                            y1, y2 = min(ry1, ry2), max(ry1, ry2)
                            s_nr = _seite_von(obj)
                            key = (name, s_nr)
                            if key not in gefunden:
                                gefunden.add(key)
                                felder.append({
                                    "name": name,
                                    "seite": s_nr + 1,
                                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                })
                        except Exception:
                            pass

        root_fields = (
            reader.trailer.get("/Root", {})
            .get("/AcroForm", {})
            .get("/Fields", [])
        )
        _walk_felder(root_fields)

        return JsonResponse({"felder": felder, "seiten": seiten})
    except Exception as exc:
        logger.error("Felder-JSON Fehler (Analyse %d): %s", pk, exc)
        return JsonResponse({"fehler": str(exc)}, status=500)


@portal_login_required
def analyse_status_json(request, pk):
    """Polling-Endpunkt für JavaScript."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)
    return JsonResponse({
        "status": analyse.status,
        "fehler": analyse.fehler_meldung,
        "hat_ergebnis": analyse.ergebnis_json is not None,
        "pfad_pk": analyse.importierter_pfad_pk,
    })


@portal_login_required
@require_POST
def analyse_importieren(request, pk):
    """Importiert das Analyse-Ergebnis als Pfad in Vorgangswerk (direkter Import, ohne Review)."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    if analyse.status != FormularAnalyse.STATUS_FERTIG:
        messages.error(request, "Analyse noch nicht abgeschlossen.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    if not analyse.ergebnis_json:
        messages.error(request, "Kein Analyseergebnis vorhanden.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    pfad_pk = importiere_pfad_aus_analyse(analyse)
    messages.success(request, "Pfad erfolgreich importiert! Du kannst ihn jetzt im Editor bearbeiten.")
    return redirect(f"/formulare/editor/{pfad_pk}/")


@portal_login_required
@require_POST
def analyse_koordinaten_speichern(request, pk):
    """AJAX POST: Speichert x_pct/y_pct Koordinaten für Overlay-Befüllung."""
    import copy
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    try:
        data = json.loads(request.body)
        felder = data.get("felder", [])
    except Exception as exc:
        return JsonResponse({"ok": False, "fehler": str(exc)}, status=400)

    koord_map = {f["id"]: f for f in felder if "id" in f}

    ergebnis = copy.deepcopy(analyse.ergebnis_json or {})
    for schritt in ergebnis.get("schritte", []):
        for feld in schritt.get("felder_json", []):
            if feld.get("id") in koord_map:
                k = koord_map[feld["id"]]
                feld["x_pct"] = round(float(k.get("x_pct", 0)), 4)
                feld["y_pct"] = round(float(k.get("y_pct", 0)), 4)
                feld["seite_nr"] = int(k.get("seite_nr", 0))
                if "vorlage" in k:
                    feld["vorlage"] = k["vorlage"]
                if "optionen_koord" in k:
                    feld["optionen_koord"] = k["optionen_koord"]

    # Schrift-Einstellungen speichern
    if "pdf_font" in data:
        ergebnis["pdf_font"] = {
            "size": max(6, min(24, float(data["pdf_font"].get("size", 9)))),
            "bold": bool(data["pdf_font"].get("bold", False)),
        }

    analyse.ergebnis_json = ergebnis
    analyse.save(update_fields=["ergebnis_json"])

    if analyse.importierter_pfad_pk:
        from formulare.models import AntrSchritt
        for schritt in AntrSchritt.objects.filter(pfad_id=analyse.importierter_pfad_pk):
            felder_json = schritt.felder_json or []
            changed = False
            for feld in felder_json:
                if feld.get("id") in koord_map:
                    k = koord_map[feld["id"]]
                    feld["x_pct"] = round(float(k.get("x_pct", 0)), 4)
                    feld["y_pct"] = round(float(k.get("y_pct", 0)), 4)
                    feld["seite_nr"] = int(k.get("seite_nr", 0))
                    if "vorlage" in k:
                        feld["vorlage"] = k["vorlage"]
                    if "optionen_koord" in k:
                        feld["optionen_koord"] = k["optionen_koord"]
                    changed = True
            if changed:
                schritt.felder_json = felder_json
                schritt.save(update_fields=["felder_json"])

    logger.info("Koordinaten gespeichert: Analyse %d, %d Felder", pk, len(koord_map))
    return JsonResponse({"ok": True})


@portal_login_required
def analyse_pruefen(request, pk):
    """Zwischenschritt: Felder prüfen und Typen anpassen vor dem Import."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    if analyse.status not in (FormularAnalyse.STATUS_FERTIG, FormularAnalyse.STATUS_IMPORTIERT):
        messages.error(request, "Analyse noch nicht abgeschlossen.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    if not analyse.ergebnis_json:
        messages.error(request, "Kein Analyseergebnis vorhanden.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    if request.method == "POST":
        try:
            geaendert_json_str = request.POST.get("ergebnis_json", "")
            geaendert_json = json.loads(geaendert_json_str)
            from .services import PfadDefinition
            pfad_def = PfadDefinition.model_validate(geaendert_json)
            analyse.ergebnis_json = pfad_def.model_dump()
            analyse.save(update_fields=["ergebnis_json"])
            pfad_pk = importiere_pfad_aus_analyse(analyse)
            messages.success(request, "Pfad erfolgreich importiert! Du kannst ihn jetzt im Editor bearbeiten.")
            return redirect(f"/formulare/editor/{pfad_pk}/")
        except Exception as e:
            logger.exception("Fehler beim Prüf-Import für Analyse %d: %s", pk, e)
            messages.error(request, f"Fehler beim Import: {e}")

    import json as _json

    # Wenn Pfad bereits importiert: felder_json live aus AntrSchritt einmergen
    # (damit nach dem Import im Editor angelegte Felder auch hier erscheinen)
    ergebnis = analyse.ergebnis_json
    if analyse.importierter_pfad_pk:
        try:
            from formulare.models import AntrSchritt
            # Koordinaten-Index aus ergebnis_json aufbauen {feld_id: {x_pct, y_pct, seite_nr}}
            koord_index: dict = {}
            for s in (ergebnis.get("schritte") or []):
                for f in (s.get("felder_json") or []):
                    fid = f.get("id")
                    if fid:
                        koord_index[fid] = {
                            "x_pct": f.get("x_pct", 0),
                            "y_pct": f.get("y_pct", 0),
                            "seite_nr": f.get("seite_nr", 0),
                        }
            # Schritte aus DB neu aufbauen, Koordinaten übertragen
            neue_schritte = []
            for schritt in AntrSchritt.objects.filter(pfad_id=analyse.importierter_pfad_pk):
                felder = []
                for f in (schritt.felder_json or []):
                    f = dict(f)
                    if f.get("id") in koord_index:
                        f.update(koord_index[f["id"]])
                    felder.append(f)
                neue_schritte.append({
                    "node_id": schritt.node_id,
                    "titel": schritt.titel,
                    "ist_start": schritt.ist_start,
                    "ist_ende": schritt.ist_ende,
                    "loop_bezeichnung": schritt.loop_bezeichnung or "",
                    "felder_json": felder,
                })
            ergebnis = dict(ergebnis)
            ergebnis["schritte"] = neue_schritte
        except Exception as exc:
            logger.warning("analyse_pruefen: Schritt-Merge fehlgeschlagen – %s", exc)

    ergebnis_json_str = _json.dumps(ergebnis, ensure_ascii=False)
    pdf_font_json = _json.dumps(ergebnis.get("pdf_font") or {"size": 9, "bold": False})
    bereits_importiert = analyse.status == FormularAnalyse.STATUS_IMPORTIERT
    return render(request, "portal/analyse_pruefen.html", {
        "account": account,
        "analyse": analyse,
        "ergebnis_json_str": ergebnis_json_str,
        "pdf_font_json": pdf_font_json,
        "bereits_importiert": bereits_importiert,
    })


# ---------------------------------------------------------------------------
# Credits / Stripe
# ---------------------------------------------------------------------------

@portal_login_required
def credits_kaufen(request):
    account = request.user.portal_account
    return render(request, "portal/credits_kaufen.html", {
        "account": account,
        "pakete": CREDIT_PAKETE,
        "stripe_public_key": getattr(settings, "STRIPE_PUBLIC_KEY", ""),
    })


@portal_login_required
@require_POST
def checkout_starten(request, paket_id):
    """Erstellt eine Stripe Checkout Session und leitet zur Zahlungsseite weiter."""
    paket = CREDIT_PAKETE_BY_ID.get(paket_id)
    if not paket:
        messages.error(request, "Ungültiges Paket.")
        return redirect(reverse("portal:credits_kaufen"))

    stripe_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not stripe_key:
        messages.error(request, "Stripe ist nicht konfiguriert.")
        return redirect(reverse("portal:credits_kaufen"))

    import stripe
    stripe.api_key = stripe_key

    account = request.user.portal_account
    erfolg_url = request.build_absolute_uri(
        reverse("portal:credits_erfolg") + f"?paket={paket_id}&credits={paket['credits']}"
    )
    abbruch_url = request.build_absolute_uri(reverse("portal:credits_kaufen"))

    # Stripe Customer anlegen oder wiederverwenden
    if not account.stripe_customer_id:
        customer = stripe.Customer.create(email=request.user.email)
        account.stripe_customer_id = customer.id
        account.save(update_fields=["stripe_customer_id"])

    session = stripe.checkout.Session.create(
        customer=account.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Vorgangswerk Portal – {paket['name']} ({paket['credits']} Credits)",
                },
                "unit_amount": paket["preis_cent"],
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=erfolg_url + "&session_id={CHECKOUT_SESSION_ID}",
        cancel_url=abbruch_url,
        metadata={
            "portal_account_id": str(account.pk),
            "paket_id": paket_id,
            "credits": str(paket["credits"]),
        },
    )

    return redirect(session.url, permanent=False)


@portal_login_required
def credits_erfolg(request):
    """Erfolgsseite nach Stripe-Zahlung. Credits werden per Webhook gutgeschrieben."""
    account = request.user.portal_account
    credits = request.GET.get("credits", "?")
    paket_id = request.GET.get("paket", "")
    paket = CREDIT_PAKETE_BY_ID.get(paket_id, {})
    return render(request, "portal/credits_erfolg.html", {
        "account": account,
        "credits": credits,
        "paket": paket,
    })


@csrf_exempt
def stripe_webhook(request):
    """
    Stripe Webhook-Endpunkt.
    Verarbeitet checkout.session.completed → Credits gutschreiben.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    webhook_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")

    import stripe
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", "")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning("Stripe Webhook ungültig: %s", e)
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        account_id = metadata.get("portal_account_id")
        credits = int(metadata.get("credits", 0))
        paket_id = metadata.get("paket_id", "")
        payment_intent = session.get("payment_intent", "")

        if account_id and credits > 0:
            try:
                account = PortalAccount.objects.get(pk=account_id)
                account.credit_gutschreiben(
                    credits,
                    f"Kauf Paket '{paket_id}': {credits} Credits",
                    stripe_pi=payment_intent or "",
                )
                logger.info("Credits gutgeschrieben: Account %s, %d Credits", account_id, credits)
            except PortalAccount.DoesNotExist:
                logger.error("PortalAccount %s nicht gefunden", account_id)

    return HttpResponse(status=200)
