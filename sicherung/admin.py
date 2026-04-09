# SPDX-License-Identifier: EUPL-1.2
from django.contrib import admin
from .models import SicherungsProtokoll


@admin.register(SicherungsProtokoll)
class SicherungsProtokollAdmin(admin.ModelAdmin):
    list_display = ["dateiname", "typ", "rhythmus", "status", "groesse_bytes", "verschluesselt", "erstellt_am", "geprueft_am"]
    list_filter = ["typ", "rhythmus", "status", "verschluesselt"]
    readonly_fields = ["erstellt_am", "geprueft_am", "geloescht_am", "sha256_pruefsumme"]
