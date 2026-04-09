# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "quiz"

urlpatterns = [
    # Ergebnisse
    path("ergebnisse/<int:pfad_pk>/",  views.ergebnisse,      name="ergebnisse"),
    path("ergebnis/<int:pk>/",         views.ergebnis_detail,  name="ergebnis_detail"),
    # Öffentlich (kein Login)
    path("zertifikat/<uuid:token>/",       views.zertifikat_pruefen,  name="zertifikat_pruefen"),
    path("zertifikat/<uuid:token>/pdf/",   views.zertifikat_download, name="zertifikat_download"),
    # Import-API (Staff only)
    path("import/ki/",                 views.fragen_aus_ki,   name="import_ki"),
    path("import/csv/",                views.fragen_aus_csv,  name="import_csv"),
    path("import/demo/<str:name>/",    views.demo_deck,       name="demo_deck"),
    # Fragenpools (Staff only)
    path("pools/",                          views.pool_liste,                name="pool_liste"),
    path("pools/neu/",                      views.pool_neu,                  name="pool_neu"),
    path("pools/json/",                     views.pools_json,                name="pools_json"),
    path("pools/<int:pk>/",                 views.pool_detail,               name="pool_detail"),
    path("pools/<int:pk>/loeschen/",        views.pool_loeschen,             name="pool_loeschen"),
    path("pools/<int:pk>/fragen/",          views.pool_fragen_speichern,     name="pool_fragen_speichern"),
    path("pools/<int:pk>/json/",            views.pool_als_json,             name="pool_als_json"),
    path("pools/<int:pk>/aus-portal/",      views.pool_aus_portal_importieren, name="pool_aus_portal"),
]
