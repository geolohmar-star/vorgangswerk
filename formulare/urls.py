# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "formulare"

# ---------------------------------------------------------------------------
# Interne Routen (Login erforderlich)
# ---------------------------------------------------------------------------
urlpatterns = [
    # Uebersicht
    path("", views.pfad_liste, name="liste"),
    path("neu/", views.pfad_neu, name="pfad_neu"),
    # Editor
    path("editor/<int:pk>/", views.pfad_editor, name="pfad_editor"),
    path("editor/laden/<int:pk>/", views.pfad_editor_laden, name="pfad_editor_laden"),
    path("editor/speichern/", views.pfad_editor_speichern, name="pfad_editor_speichern"),
    path("editor/scanner/", views.pfad_scanner, name="pfad_scanner"),
    path("editor/versionen/<int:pk>/", views.pfad_versionen, name="pfad_versionen"),
    path("editor/version/<int:version_pk>/", views.pfad_version_laden, name="pfad_version_laden"),
    path("blockansicht/<int:pk>/", views.pfad_blockansicht, name="pfad_blockansicht"),
    path("loeschen/<int:pk>/", views.pfad_loeschen, name="pfad_loeschen"),
    path("kategorie/<int:pk>/", views.pfad_kategorie_setzen, name="pfad_kategorie_setzen"),
    # Player (eingeloggte Nutzer)
    path("starten/<int:pk>/", views.pfad_starten, name="pfad_starten"),
    path("sitzung/<int:sitzung_pk>/", views.pfad_schritt, name="pfad_schritt"),
    path("sitzung/<int:sitzung_pk>/abgeschlossen/", views.pfad_abgeschlossen, name="pfad_abgeschlossen"),
    path("meine/", views.meine_antraege, name="meine_antraege"),
    path("sitzung/<int:pk>/loeschen/", views.sitzung_loeschen, name="sitzung_loeschen"),
    path("sitzung/<int:pk>/pdf/", views.sitzung_pdf, name="sitzung_pdf"),
    # Auswertung
    path("auswertung/<int:pk>/", views.pfad_auswertung, name="pfad_auswertung"),
]

# ---------------------------------------------------------------------------
# Oeffentliche Routen (kein Login) – werden in config/urls.py eingebunden
# ---------------------------------------------------------------------------
public_urlpatterns = [
    path("<str:kuerzel>/", views.antrag_oeffentlich, name="antrag_oeffentlich"),
    path("<str:kuerzel>/starten/", views.antrag_oeffentlich_starten, name="antrag_oeffentlich_starten"),
    path("s/<int:sitzung_pk>/", views.antrag_oeffentlich_schritt, name="antrag_oeffentlich_schritt"),
    path("s/<int:sitzung_pk>/abgeschlossen/", views.antrag_oeffentlich_abgeschlossen, name="antrag_oeffentlich_abgeschlossen"),
    path("fehler/", views.antrag_oeffentlich_fehler, name="antrag_oeffentlich_fehler"),
]
