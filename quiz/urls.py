# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "quiz"

urlpatterns = [
    # Admin
    path("ergebnisse/<int:pfad_pk>/",  views.ergebnisse,      name="ergebnisse"),
    path("ergebnis/<int:pk>/",         views.ergebnis_detail,  name="ergebnis_detail"),
    # Öffentlich (kein Login)
    path("zertifikat/<uuid:token>/",       views.zertifikat_pruefen,  name="zertifikat_pruefen"),
    path("zertifikat/<uuid:token>/pdf/",   views.zertifikat_download, name="zertifikat_download"),
    # Import-API (Staff only)
    path("import/ki/",                 views.fragen_aus_ki,   name="import_ki"),
    path("import/csv/",                views.fragen_aus_csv,  name="import_csv"),
    path("import/demo/<str:name>/",    views.demo_deck,       name="demo_deck"),
]
