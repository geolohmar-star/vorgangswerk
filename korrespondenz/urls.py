# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path

from . import views

app_name = "korrespondenz"

urlpatterns = [
    # Briefvorgaenge
    path("",                          views.brief_liste,          name="brief_liste"),
    path("neu/",                      views.brief_erstellen,      name="brief_erstellen"),
    path("<int:pk>/",                 views.brief_detail,         name="brief_detail"),
    path("<int:pk>/download/",        views.brief_download,       name="brief_download"),
    path("<int:pk>/pdf/",             views.brief_pdf_download,   name="brief_pdf_download"),
    path("<int:pk>/xoev/",            views.brief_xoev_export,    name="brief_xoev_export"),
    path("<int:pk>/status/",          views.brief_status_aendern, name="brief_status_aendern"),
    path("<int:pk>/loeschen/",        views.brief_loeschen,       name="brief_loeschen"),
    path("<int:pk>/editor/",          views.brief_editor,         name="brief_editor"),
    path("<int:pk>/oo-download/",     views.brief_oo_download,    name="brief_oo_download"),
    path("<int:pk>/oo-callback/",     views.brief_oo_callback,    name="brief_oo_callback"),
    path("<int:pk>/oo-forcesave/",    views.brief_oo_forcesave,   name="brief_oo_forcesave"),
    path("<int:pk>/oo-version/",      views.brief_oo_version,     name="brief_oo_version"),
    # Briefvorlagen
    path("vorlagen/",                         views.vorlage_liste,       name="vorlage_liste"),
    path("vorlagen/hochladen/",               views.vorlage_hochladen,   name="vorlage_hochladen"),
    path("vorlagen/generieren/",              views.vorlage_generieren,  name="vorlage_generieren"),
    path("firmendaten/",                      views.firmendaten,          name="firmendaten"),
    path("bankverbindungen/",                views.bankverbindungen,          name="bankverbindungen"),
    path("bankverbindungen/neu/",            views.bankverbindung_speichern,  name="bankverbindung_neu"),
    path("bankverbindungen/<int:pk>/",       views.bankverbindung_speichern,  name="bankverbindung_bearbeiten"),
    path("bankverbindungen/<int:pk>/loeschen/", views.bankverbindung_loeschen, name="bankverbindung_loeschen"),
    path("vorlagen/<int:pk>/download/",        views.vorlage_download,    name="vorlage_download"),
    path("vorlagen/<int:pk>/bearbeiten/",     views.vorlage_bearbeiten,  name="vorlage_bearbeiten"),
    path("vorlagen/<int:pk>/klonen/",         views.vorlage_klonen,      name="vorlage_klonen"),
    path("vorlagen/<int:pk>/loeschen/",       views.vorlage_loeschen,    name="vorlage_loeschen"),
    path("vorlagen/<int:pk>/editor/",         views.vorlage_editor,      name="vorlage_editor"),
    path("vorlagen/<int:pk>/oo-download/",    views.vorlage_oo_download,  name="vorlage_oo_download"),
    path("vorlagen/<int:pk>/oo-callback/",    views.vorlage_oo_callback,  name="vorlage_oo_callback"),
    path("vorlagen/<int:pk>/oo-forcesave/",   views.vorlage_oo_forcesave, name="vorlage_oo_forcesave"),
    path("vorlagen/<int:pk>/oo-version/",     views.vorlage_oo_version,   name="vorlage_oo_version"),
    path("vorlagen/<int:pk>/defaults/",       views.vorlage_defaults,    name="vorlage_defaults"),
    path("vorlagen/<int:pk>/platzhalter/",    views.vorlage_platzhalter, name="vorlage_platzhalter"),
    # WOPI fuer Collabora (Briefvorlagen)
    path("wopi/vorlagen/<int:pk>/",          views.wopi_vorlage_files,    name="wopi_vorlage_files"),
    path("wopi/vorlagen/<int:pk>",           views.wopi_vorlage_files),
    path("wopi/vorlagen/<int:pk>/contents/", views.wopi_vorlage_contents, name="wopi_vorlage_contents"),
    path("wopi/vorlagen/<int:pk>/contents",  views.wopi_vorlage_contents),
    # WOPI fuer Collabora (Briefvorgaenge)
    path("wopi/briefe/<int:pk>/",            views.wopi_brief_files,    name="wopi_brief_files"),
    path("wopi/briefe/<int:pk>",             views.wopi_brief_files),
    path("wopi/briefe/<int:pk>/contents/",   views.wopi_brief_contents, name="wopi_brief_contents"),
    path("wopi/briefe/<int:pk>/contents",    views.wopi_brief_contents),
    # Bescheid-Generator
    path("bescheid/",                             views.bescheid_suche,            name="bescheid_suche"),
    path("bescheid/<int:sitzung_pk>/felder/",     views.bescheid_platzhalter_json, name="bescheid_platzhalter_json"),
]
