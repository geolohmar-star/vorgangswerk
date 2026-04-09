# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""
Portal-Views: Registrierung, Dashboard, PDF-Upload, Stripe-Checkout.
"""
import json
import logging
import threading
import re

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

from .models import PortalAccount, FormularAnalyse, CreditTransaktion, CREDIT_PAKETE, CREDIT_PAKETE_BY_ID
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

def registrierung(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        passwort1 = request.POST.get("passwort1", "")
        passwort2 = request.POST.get("passwort2", "")

        # Validierung
        fehler = []
        if not email or "@" not in email:
            fehler.append("Bitte eine gültige E-Mail-Adresse eingeben.")
        if passwort1 != passwort2:
            fehler.append("Die Passwörter stimmen nicht überein.")
        if len(passwort1) < 12:
            fehler.append("Das Passwort muss mindestens 12 Zeichen lang sein.")
        if User.objects.filter(username=email).exists():
            fehler.append("Diese E-Mail-Adresse ist bereits registriert.")

        if fehler:
            return render(request, "portal/registrierung.html", {"fehler": fehler, "email": email})

        # Benutzer anlegen
        user = User.objects.create_user(
            username=email,
            email=email,
            password=passwort1,
            is_staff=False,
            is_superuser=False,
        )
        account = PortalAccount.objects.create(user=user, credits=0, email_verifiziert=False)
        token = account.neues_verifikations_token()

        # Verifizierungs-E-Mail senden
        _sende_verifikationsmail(request, user.email, token)

        messages.success(request, "Konto erstellt! Bitte prüfe deine E-Mails zur Bestätigung.")
        return redirect(reverse("portal:login"))

    return render(request, "portal/registrierung.html", {})


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

        # Credit abziehen
        if not account.credit_abziehen(1, f"Analyse: {datei.name[:80]}"):
            messages.error(request, "Nicht genug Credits.")
            return redirect(reverse("portal:credits_kaufen"))

        # Analyse-Job erstellen
        analyse = FormularAnalyse.objects.create(
            account=account,
            dateiname=datei.name[:255],
            pdf_inhalt=pdf_bytes,
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
    """Importiert das Analyse-Ergebnis als Pfad in Vorgangswerk."""
    account = request.user.portal_account
    analyse = get_object_or_404(FormularAnalyse, pk=pk, account=account)

    if analyse.status != FormularAnalyse.STATUS_FERTIG:
        messages.error(request, "Analyse noch nicht abgeschlossen.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    if not analyse.ergebnis_json:
        messages.error(request, "Kein Analyseergebnis vorhanden.")
        return redirect(reverse("portal:analyse_detail", args=[pk]))

    pfad_pk = importiere_pfad_aus_analyse(analyse)
    messages.success(request, f"Pfad erfolgreich importiert! Du kannst ihn jetzt im Editor bearbeiten.")
    return redirect(f"/formulare/editor/{pfad_pk}/")


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
