# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "workflow"

urlpatterns = [
    path("", views.workflow_liste, name="liste"),
]
