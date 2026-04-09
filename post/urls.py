# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

from django.urls import path
from . import views

app_name = "post"

urlpatterns = [
    path("", views.postbuch_liste, name="liste"),
    path("neu/", views.posteintrag_neu, name="neu"),
    path("<int:pk>/bearbeiten/", views.posteintrag_bearbeiten, name="bearbeiten"),
    path("<int:pk>/loeschen/", views.posteintrag_loeschen, name="loeschen"),
    # Organisationsverzeichnis
    path("organisationen/", views.org_liste, name="org_liste"),
    path("organisationen/neu/", views.org_neu, name="org_neu"),
    path("organisationen/<int:pk>/", views.org_bearbeiten, name="org_bearbeiten"),
    path("organisationen/<int:pk>/loeschen/", views.org_loeschen, name="org_loeschen"),
    path("organisationen/autocomplete/", views.org_autocomplete, name="org_autocomplete"),
    # CSV-Export
    path("export/csv/", views.postbuch_csv, name="csv_export"),
    # Verteiler-Quittierung (oeffentlich)
    path("bestaetigung/<uuid:token>/", views.verteiler_bestaetigung, name="bestaetigung"),
    # Verteiler-Aktionen (Login erforderlich)
    path("verteiler/<int:pk>/manuell/", views.verteiler_manuell_erledigt, name="verteiler_manuell"),
    path("verteiler/<int:pk>/erneut/", views.verteiler_erneut_senden, name="verteiler_erneut"),
]
