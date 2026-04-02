# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin

from .models import Benachrichtigung, EingehendeEmail, EmailAnhang


class EmailAnhangInline(admin.TabularInline):
    model = EmailAnhang
    extra = 0
    fields = ["dateiname", "dateityp", "groesse_bytes"]
    readonly_fields = ["dateiname", "dateityp", "groesse_bytes"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EingehendeEmail)
class EingehendeEmailAdmin(admin.ModelAdmin):
    list_display = [
        "betreff", "absender_email", "absender_name",
        "status", "empfangen_am", "importiert_am",
    ]
    list_filter = ["status", "empfangen_am"]
    search_fields = ["betreff", "absender_email", "absender_name", "inhalt_text"]
    readonly_fields = ["message_id", "importiert_am", "empfangen_am"]
    inlines = [EmailAnhangInline]
    fieldsets = [
        ("E-Mail", {
            "fields": ["betreff", "absender_name", "absender_email", "empfaenger_email",
                       "empfangen_am", "message_id"]
        }),
        ("Inhalt", {
            "fields": ["inhalt_text", "inhalt_html"]
        }),
        ("Bearbeitung", {
            "fields": ["status", "zugewiesen_an", "notiz", "importiert_am"]
        }),
    ]


@admin.register(Benachrichtigung)
class BenachrichtigungAdmin(admin.ModelAdmin):
    list_display = ["titel", "user", "typ", "gelesen", "erstellt_am"]
    list_filter = ["typ", "gelesen"]
    search_fields = ["titel", "nachricht", "user__username"]
    readonly_fields = ["erstellt_am", "gelesen_am"]
