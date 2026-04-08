# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from .models import PortalAccount, FormularAnalyse, CreditTransaktion


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


@admin.register(CreditTransaktion)
class CreditTransaktionAdmin(admin.ModelAdmin):
    list_display = ["account", "typ", "betrag", "beschreibung", "erstellt_am"]
    list_filter = ["typ"]
    search_fields = ["account__user__email", "stripe_payment_intent"]
    readonly_fields = ["erstellt_am"]
