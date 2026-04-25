# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import PortalAccount, FormularAnalyse, CreditTransaktion, Einladung


@admin.register(PortalAccount)
class PortalAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "credits", "email_verifiziert", "stripe_customer_id", "erstellt_am"]
    search_fields = ["user__email"]
    readonly_fields = ["erstellt_am", "verifikations_token"]


@admin.register(FormularAnalyse)
class FormularAnalyseAdmin(admin.ModelAdmin):
    list_display = ["dateiname", "account", "status", "credits_verbraucht", "erstellt_am", "fertig_am"]
    list_filter = ["status"]
    search_fields = ["dateiname", "account__user__email"]
    readonly_fields = ["erstellt_am", "fertig_am", "ergebnis_json", "fehler_meldung"]


@admin.register(Einladung)
class EinladungAdmin(admin.ModelAdmin):
    list_display = ["email", "start_credits", "erstellt_am", "gueltig_bis", "eingeloest_am", "eingeloest_von", "notiz"]
    list_filter = ["eingeloest_am"]
    search_fields = ["email", "notiz"]
    readonly_fields = ["token", "erstellt_am", "eingeloest_am", "eingeloest_von"]
    fields = ["email", "start_credits", "gueltig_bis", "notiz", "token", "erstellt_am", "eingeloest_am", "eingeloest_von"]
    actions = ["einladung_per_email_senden"]

    def einladung_per_email_senden(self, request, queryset):
        gesendet = 0
        for einladung in queryset.filter(eingeloest_am__isnull=True):
            link = request.build_absolute_uri(f"/portal/registrierung/{einladung.token}/")
            try:
                send_mail(
                    subject="Einladung zum Vorgangswerk Portal",
                    message=(
                        f"Hallo,\n\n"
                        f"du wurdest eingeladen, das Vorgangswerk Portal zu nutzen.\n\n"
                        f"Registriere dich hier:\n{link}\n\n"
                        f"{'Dein Konto wird mit ' + str(einladung.start_credits) + ' Credits ausgestattet.' if einladung.start_credits else ''}\n\n"
                        f"Vorgangswerk"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[einladung.email],
                    fail_silently=False,
                )
                gesendet += 1
            except Exception as e:
                self.message_user(request, f"Fehler bei {einladung.email}: {e}", level="error")
        self.message_user(request, f"{gesendet} Einladung(en) verschickt.")
    einladung_per_email_senden.short_description = "Einladungs-E-Mail senden"


@admin.register(CreditTransaktion)
class CreditTransaktionAdmin(admin.ModelAdmin):
    list_display = ["account", "typ", "betrag", "beschreibung", "erstellt_am"]
    list_filter = ["typ"]
    search_fields = ["account__user__email", "stripe_payment_intent"]
    readonly_fields = ["erstellt_am"]
