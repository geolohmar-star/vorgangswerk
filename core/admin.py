# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin
from .models import AuditLog, Benutzerprofil


@admin.register(Benutzerprofil)
class BenutzerprofilAdmin(admin.ModelAdmin):
    list_display = ["user", "abteilung", "telefon"]
    search_fields = ["user__username", "user__last_name", "abteilung"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["zeitpunkt", "user", "aktion", "app", "objekt_typ", "ip_adresse"]
    list_filter = ["aktion", "app"]
    search_fields = ["user__username", "beschreibung"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
