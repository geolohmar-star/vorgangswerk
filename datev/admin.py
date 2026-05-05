# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from .models import DatevToken


@admin.register(DatevToken)
class DatevTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "consultant_number", "client_number", "expires_at", "aktualisiert_am")
    readonly_fields = ("erstellt_am", "aktualisiert_am")
    search_fields = ("user__username", "consultant_number", "client_number")
