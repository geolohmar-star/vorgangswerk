# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("profil/", views.profil, name="profil"),
    path("leika-autocomplete/", views.leika_autocomplete, name="leika_autocomplete"),
    path("roadmap/", views.roadmap, name="roadmap"),
    path("ueber/", views.ueber, name="ueber"),
]
