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
    path("", views.pfad_liste, name="pfad_liste"),  # Alias
    path("neu/", views.pfad_neu, name="pfad_neu"),
    # Editor
    path("editor/<int:pk>/", views.pfad_editor, name="pfad_editor"),
    path("editor/laden/<int:pk>/", views.pfad_editor_laden, name="pfad_editor_laden"),
    path("editor/speichern/", views.pfad_editor_speichern, name="pfad_editor_speichern"),
    path("editor/scanner/", views.pfad_scanner, name="pfad_scanner"),
    path("editor/scanner-url/", views.pfad_scanner_url, name="pfad_scanner_url"),
    path("editor/versionen/<int:pk>/", views.pfad_versionen, name="pfad_versionen"),
    path("editor/version/<int:version_pk>/", views.pfad_version_laden, name="pfad_version_laden"),
    path("blockansicht/<int:pk>/", views.pfad_blockansicht, name="pfad_blockansicht"),
    path("loeschen/<int:pk>/", views.pfad_loeschen, name="pfad_loeschen"),
    path("kopieren/<int:pk>/", views.pfad_kopieren, name="pfad_kopieren"),
    path("exportieren/<int:pk>/", views.pfad_exportieren, name="pfad_exportieren"),
    path("importieren/", views.pfad_importieren, name="pfad_importieren"),
    path("kategorie/<int:pk>/", views.pfad_kategorie_setzen, name="pfad_kategorie_setzen"),
    # Player (eingeloggte Nutzer)
    path("starten/<int:pk>/", views.pfad_starten, name="pfad_starten"),
    path("sitzung/<int:sitzung_pk>/", views.pfad_schritt, name="pfad_schritt"),
    path("sitzung/<int:sitzung_pk>/abgeschlossen/", views.pfad_abgeschlossen, name="pfad_abgeschlossen"),
    path("meine/", views.meine_antraege, name="meine_antraege"),
    path("sitzung/<int:pk>/loeschen/", views.sitzung_loeschen, name="sitzung_loeschen"),
    path("sitzung/<int:pk>/pdf/", views.sitzung_pdf, name="sitzung_pdf"),
    path("sitzung/<int:pk>/gesamtakte/", views.sitzung_gesamtakte_zip, name="sitzung_gesamtakte"),
    path("datei/<int:pk>/", views.datei_download, name="datei_download"),
    # Webhook-Verwaltung
    path("webhooks/", views.webhooks, name="webhooks"),
    path("webhooks/neu/", views.webhook_neu, name="webhook_neu"),
    path("webhooks/<int:pk>/", views.webhook_bearbeiten, name="webhook_bearbeiten"),
    path("webhooks/<int:pk>/loeschen/", views.webhook_loeschen, name="webhook_loeschen"),
    path("webhooks/<int:pk>/log/", views.webhook_log, name="webhook_log"),
    path("webhooks/<int:pk>/testen/", views.webhook_testen, name="webhook_testen"),
    # Auswertung
    path("auswertung/<int:pk>/", views.pfad_auswertung, name="pfad_auswertung"),
    # AGS-Lookup
    path("ags/", views.ags_suche, name="ags_suche"),
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
