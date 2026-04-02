# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin

from .models import Dokument, DokumentKategorie, DokumentTag, DokumentVersion, ZugriffsProtokoll


@admin.register(DokumentKategorie)
class DokumentKategorieAdmin(admin.ModelAdmin):
    list_display = ["name", "elternkategorie", "sortierung"]
    list_filter = ["elternkategorie"]
    search_fields = ["name"]
    ordering = ["sortierung", "name"]


@admin.register(DokumentTag)
class DokumentTagAdmin(admin.ModelAdmin):
    list_display = ["name", "farbe"]
    search_fields = ["name"]


class DokumentVersionInline(admin.TabularInline):
    model = DokumentVersion
    extra = 0
    fields = ["version_nr", "groesse_bytes", "erstellt_von", "erstellt_am", "kommentar"]
    readonly_fields = ["version_nr", "groesse_bytes", "erstellt_am"]
    ordering = ["-version_nr"]


@admin.register(Dokument)
class DokumentAdmin(admin.ModelAdmin):
    list_display = [
        "titel", "dateiname", "dateityp", "version",
        "kategorie", "erstellt_von", "erstellt_am",
    ]
    list_filter = ["kategorie", "dateityp"]
    search_fields = ["titel", "dateiname"]
    readonly_fields = ["erstellt_am", "geaendert_am", "wopi_token", "wopi_token_ablauf"]
    filter_horizontal = ["tags"]
    inlines = [DokumentVersionInline]
    fieldsets = [
        ("Grunddaten", {
            "fields": ["titel", "dateiname", "dateityp", "kategorie", "tags", "gueltig_bis"]
        }),
        ("Versionierung", {
            "fields": ["version", "erstellt_von", "erstellt_am", "geaendert_am"]
        }),
        ("WOPI", {
            "classes": ["collapse"],
            "fields": ["wopi_token", "wopi_token_ablauf"],
        }),
    ]


@admin.register(ZugriffsProtokoll)
class ZugriffsProtokollAdmin(admin.ModelAdmin):
    list_display = ["zeitpunkt", "aktion", "dokument_titel", "user", "ip_adresse"]
    list_filter = ["aktion"]
    search_fields = ["dokument_titel", "user__username", "notiz"]
    readonly_fields = [
        "zeitpunkt", "aktion", "dokument", "dokument_titel",
        "user", "ip_adresse", "notiz",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
