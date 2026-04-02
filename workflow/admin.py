# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.contrib import admin

from .models import (
    ProzessAntrag,
    WorkflowInstance,
    WorkflowStep,
    WorkflowTask,
    WorkflowTemplate,
    WorkflowTransition,
    WorkflowTrigger,
)


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0
    fields = [
        "titel",
        "reihenfolge",
        "schritt_typ",
        "aktion_typ",
        "zustaendig_rolle",
        "zustaendig_gruppe",
        "zustaendig_user",
        "frist_tage",
    ]
    ordering = ["reihenfolge"]


class WorkflowTransitionInline(admin.TabularInline):
    model = WorkflowTransition
    extra = 0
    fk_name = "template"
    fields = [
        "von_schritt",
        "zu_schritt",
        "bedingung_typ",
        "bedingung_entscheidung",
        "label",
        "prioritaet",
    ]


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "kategorie",
        "version",
        "ist_aktiv",
        "ist_graph_workflow",
        "anzahl_schritte",
        "erstellt_am",
    ]
    list_filter = ["ist_aktiv", "ist_graph_workflow", "kategorie"]
    search_fields = ["name", "beschreibung"]
    readonly_fields = ["erstellt_am", "aktualisiert_am", "erstellt_von"]
    inlines = [WorkflowStepInline, WorkflowTransitionInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.erstellt_von = request.user
        super().save_model(request, obj, form, change)


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = [
        "titel",
        "template",
        "reihenfolge",
        "schritt_typ",
        "aktion_typ",
        "zustaendig_rolle",
        "zustaendig_gruppe",
        "frist_tage",
    ]
    list_filter = ["template", "schritt_typ", "aktion_typ", "zustaendig_rolle"]
    search_fields = ["titel", "beschreibung", "template__name"]
    raw_id_fields = ["template"]
    fieldsets = [
        (
            "Grunddaten",
            {
                "fields": [
                    "template",
                    "titel",
                    "beschreibung",
                    "reihenfolge",
                    "schritt_typ",
                    "aktion_typ",
                    "frist_tage",
                    "ist_parallel",
                ]
            },
        ),
        (
            "Zustaendigkeit",
            {
                "fields": [
                    "zustaendig_rolle",
                    "zustaendig_gruppe",
                    "zustaendig_user",
                    "eskalation_an_gruppe",
                    "eskalation_nach_tagen",
                ]
            },
        ),
        (
            "Bedingung (bedingte Aktivierung)",
            {
                "classes": ["collapse"],
                "fields": [
                    "bedingung_feld",
                    "bedingung_operator",
                    "bedingung_wert",
                ],
            },
        ),
        (
            "Auto-Aktion",
            {
                "classes": ["collapse"],
                "fields": ["auto_config"],
            },
        ),
        (
            "Vis.js Position",
            {
                "classes": ["collapse"],
                "fields": ["node_id", "pos_x", "pos_y"],
            },
        ),
    ]


@admin.register(WorkflowTransition)
class WorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = [
        "von_schritt",
        "zu_schritt",
        "bedingung_typ",
        "bedingung_entscheidung",
        "label",
        "prioritaet",
        "template",
    ]
    list_filter = ["template", "bedingung_typ"]
    raw_id_fields = ["template", "von_schritt", "zu_schritt"]


class WorkflowTaskInline(admin.TabularInline):
    model = WorkflowTask
    extra = 0
    fields = [
        "step",
        "status",
        "zugewiesen_an_gruppe",
        "zugewiesen_an_user",
        "frist",
        "entscheidung",
        "erledigt_von",
        "erledigt_am",
    ]
    readonly_fields = ["erledigt_am"]
    ordering = ["erstellt_am"]


@admin.register(WorkflowInstance)
class WorkflowInstanceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "template",
        "status",
        "fortschritt",
        "gestartet_von",
        "gestartet_am",
        "abgeschlossen_am",
    ]
    list_filter = ["status", "template"]
    readonly_fields = [
        "content_type",
        "object_id",
        "gestartet_am",
        "abgeschlossen_am",
        "fortschritt",
    ]
    inlines = [WorkflowTaskInline]
    search_fields = ["template__name", "gestartet_von__username"]


@admin.register(WorkflowTask)
class WorkflowTaskAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "step",
        "instance",
        "status",
        "zugewiesen_an_gruppe",
        "zugewiesen_an_user",
        "frist",
        "ist_ueberfaellig_display",
        "erledigt_am",
    ]
    list_filter = ["status", "step__template", "zugewiesen_an_gruppe"]
    search_fields = [
        "step__titel",
        "zugewiesen_an_user__username",
        "erledigt_von__username",
        "kommentar",
    ]
    readonly_fields = [
        "erstellt_am",
        "erledigt_am",
        "gestartet_am",
        "claimed_am",
    ]

    @admin.display(description="Ueberfaellig", boolean=True)
    def ist_ueberfaellig_display(self, obj):
        return obj.ist_ueberfaellig


@admin.register(ProzessAntrag)
class ProzessAntragAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "antragsteller",
        "ausloeser_typ",
        "status",
        "erstellt_am",
    ]
    list_filter = ["status", "ausloeser_typ"]
    search_fields = ["name", "ziel", "antragsteller__username"]
    readonly_fields = ["erstellt_am", "aktualisiert_am"]
    fieldsets = [
        (
            "Antrag",
            {
                "fields": [
                    "antragsteller",
                    "name",
                    "ziel",
                    "ausloeser_typ",
                    "ausloeser_detail",
                    "schritte",
                    "pdf_benoetigt",
                    "team_benoetigt",
                    "team_vorschlag",
                    "bemerkungen",
                ]
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "status",
                    "workflow_instance",
                    "erstellt_am",
                    "aktualisiert_am",
                ]
            },
        ),
    ]


@admin.register(WorkflowTrigger)
class WorkflowTriggerAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "trigger_event",
        "trigger_auf",
        "content_type",
        "ist_aktiv",
        "erstellt_am",
    ]
    list_filter = ["ist_aktiv", "trigger_auf"]
    search_fields = ["name", "trigger_event", "beschreibung"]
    fieldsets = [
        (
            "Trigger-Konfiguration",
            {
                "fields": [
                    "name",
                    "beschreibung",
                    "trigger_event",
                    "trigger_auf",
                    "content_type",
                    "ist_aktiv",
                ]
            },
        ),
        (
            "Felder-Mapping",
            {
                "fields": [
                    "antragsteller_pfad",
                    "workflow_instance_feld",
                ],
                "description": (
                    "Punkt-getrennte Pfade zum User-Objekt und zum workflow_instance-Feld "
                    "auf dem verknuepften Objekt."
                ),
            },
        ),
    ]
