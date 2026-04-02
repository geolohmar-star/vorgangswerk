# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from .models import AntrDatei, AntrPfad, AntrSchritt, AntrSitzung, AntrTransition, AntrVersion


class AntrSchrittInline(admin.TabularInline):
    model = AntrSchritt
    extra = 0
    fields = ["node_id", "titel", "ist_start", "ist_ende", "pos_x", "pos_y"]


class AntrTransitionInline(admin.TabularInline):
    model = AntrTransition
    extra = 0
    fields = ["von_schritt", "zu_schritt", "bedingung", "label", "reihenfolge"]


@admin.register(AntrPfad)
class AntrPfadAdmin(admin.ModelAdmin):
    list_display = ["name", "kuerzel", "kategorie", "aktiv", "oeffentlich", "erstellt_am"]
    list_filter = ["aktiv", "oeffentlich", "kategorie"]
    search_fields = ["name", "kuerzel", "beschreibung"]
    inlines = [AntrSchrittInline, AntrTransitionInline]


@admin.register(AntrSitzung)
class AntrSitzungAdmin(admin.ModelAdmin):
    list_display = ["vorgangsnummer", "pfad", "user", "status", "gestartet_am"]
    list_filter = ["status", "pfad"]
    search_fields = ["vorgangsnummer", "user__username", "email_anonym"]
    readonly_fields = ["gestartet_am", "abgeschlossen_am", "vorgangsnummer"]


@admin.register(AntrVersion)
class AntrVersionAdmin(admin.ModelAdmin):
    list_display = ["pfad", "version_nr", "erstellt_von", "erstellt_am"]
    list_filter = ["pfad"]
    readonly_fields = ["snapshot_json", "erstellt_am"]
