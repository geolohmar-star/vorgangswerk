# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Oeffentliche Routen – kein Login erforderlich."""
from django.urls import path
from . import views

app_name = "formulare_pub"

urlpatterns = [
    path("fehler/", views.antrag_oeffentlich_fehler, name="antrag_oeffentlich_fehler"),
    path("s/<int:sitzung_pk>/", views.antrag_oeffentlich_schritt, name="antrag_oeffentlich_schritt"),
    path("s/<int:sitzung_pk>/abgeschlossen/", views.antrag_oeffentlich_abgeschlossen, name="antrag_oeffentlich_abgeschlossen"),
    path("<str:kuerzel>/starten/", views.antrag_oeffentlich_starten, name="antrag_oeffentlich_starten"),
    path("<str:kuerzel>/", views.antrag_oeffentlich, name="antrag_oeffentlich"),
]
