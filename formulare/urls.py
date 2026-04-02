# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "formulare"

urlpatterns = [
    path("", views.formular_liste, name="liste"),
]
