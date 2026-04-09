# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from .models import QuizErgebnis, QuizZertifikat, QuizFragenPool


@admin.register(QuizFragenPool)
class QuizFragenPoolAdmin(admin.ModelAdmin):
    list_display   = ("name", "anzahl", "geaendert_am")
    search_fields  = ("name", "beschreibung")
    readonly_fields = ("erstellt_am", "geaendert_am")


class QuizZertifikatInline(admin.TabularInline):
    model   = QuizZertifikat
    extra   = 0
    fields  = ("ablaufdatum", "erstellt_am", "erinnerung_gesendet")
    readonly_fields = ("erstellt_am",)


@admin.register(QuizErgebnis)
class QuizErgebnisAdmin(admin.ModelAdmin):
    list_display   = ("sitzung", "prozent", "bestanden", "note", "bewertungsmodell", "erstellt_am")
    list_filter    = ("bestanden", "bewertungsmodell")
    search_fields  = ("sitzung__vorgangsnummer",)
    readonly_fields = ("uuid", "erstellt_am", "antworten_json", "config_snapshot")
    inlines        = [QuizZertifikatInline]


@admin.register(QuizZertifikat)
class QuizZertifikatAdmin(admin.ModelAdmin):
    list_display  = ("ergebnis", "ablaufdatum", "erinnerung_gesendet", "erstellt_am")
    list_filter   = ("erinnerung_gesendet",)
    readonly_fields = ("erstellt_am",)
