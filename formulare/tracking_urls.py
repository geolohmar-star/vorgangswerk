# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Tracking-Routen fuer Buerger – kein Login erforderlich."""
from django.urls import path
from . import views

app_name = "formulare_tracking"

urlpatterns = [
    path("<str:vorgangsnummer>/", views.vorgang_tracking, name="vorgang_tracking"),
]
