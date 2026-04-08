# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path

from . import views

app_name = "workflow"

urlpatterns = [
    # ---------------------------------------------------------------------------
    # Arbeitsstapel
    # ---------------------------------------------------------------------------
    path("", views.arbeitsstapel, name="arbeitsstapel"),
    path("task/<int:pk>/", views.task_detail, name="task_detail"),
    path("task/<int:pk>/abholen/", views.task_abholen, name="task_abholen"),
    path("task/<int:pk>/zurueckgeben/", views.task_zurueckgeben, name="task_zurueckgeben"),
    path("task/<int:task_pk>/brief-erstellen/", views.workflow_brief_erstellen, name="brief_erstellen"),
    path("brief/<int:brief_pk>/signieren/", views.workflow_brief_signieren, name="brief_signieren"),

    # ---------------------------------------------------------------------------
    # Workflow-Templates
    # ---------------------------------------------------------------------------
    path("liste/", views.workflow_liste, name="liste"),
    path("detail/<int:pk>/", views.workflow_detail, name="detail"),
    path("instanz/<int:pk>/", views.instanz_detail, name="instanz_detail"),

    # ---------------------------------------------------------------------------
    # Visueller Editor
    # ---------------------------------------------------------------------------
    path("editor/", views.workflow_editor, name="editor_neu"),
    path("editor/<int:pk>/", views.workflow_editor, name="editor"),
    path("editor/save/", views.workflow_editor_save, name="editor_save"),
    path("editor/load/<int:pk>/", views.workflow_editor_load, name="editor_load"),

    # ---------------------------------------------------------------------------
    # Prozessantraege
    # ---------------------------------------------------------------------------
    path("prozessantrag/neu/", views.prozessantrag_erstellen, name="prozessantrag_erstellen"),
    path("prozessantrag/", views.prozessantrag_liste, name="prozessantrag_liste"),
    path("prozesszentrale/", views.prozesszentrale, name="prozesszentrale"),

    # ---------------------------------------------------------------------------
    # Trigger
    # ---------------------------------------------------------------------------
    path("trigger/", views.trigger_liste, name="trigger_liste"),
    path("trigger/neu/", views.trigger_erstellen, name="trigger_erstellen"),
    path("trigger/<int:pk>/", views.trigger_bearbeiten, name="trigger_bearbeiten"),
    path("trigger/<int:pk>/loeschen/", views.trigger_loeschen, name="trigger_loeschen"),

    # ---------------------------------------------------------------------------
    # API
    # ---------------------------------------------------------------------------
    path("api/content-types/", views.api_content_types, name="api_content_types"),
    path(
        "status/<int:content_type_id>/<int:object_id>/",
        views.workflow_status_partial,
        name="status_partial",
    ),
]
