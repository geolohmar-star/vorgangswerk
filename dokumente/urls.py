# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path

from . import views

app_name = "dokumente"

urlpatterns = [
    # ---------------------------------------------------------------------------
    # Liste & Upload
    # ---------------------------------------------------------------------------
    path("", views.dokument_liste, name="liste"),
    path("hochladen/", views.dokument_hochladen, name="hochladen"),

    # ---------------------------------------------------------------------------
    # Einzelnes Dokument
    # ---------------------------------------------------------------------------
    path("<int:pk>/", views.dokument_detail, name="detail"),
    path("<int:pk>/download/", views.dokument_download, name="download"),
    path("<int:pk>/vorschau/", views.dokument_vorschau, name="vorschau"),
    path("<int:pk>/bearbeiten/", views.dokument_bearbeiten, name="bearbeiten"),
    path("<int:pk>/loeschen/", views.dokument_loeschen, name="loeschen"),
    path("<int:pk>/protokoll/", views.dokument_protokoll, name="protokoll"),

    # ---------------------------------------------------------------------------
    # Versionen
    # ---------------------------------------------------------------------------
    path("<int:pk>/version/hochladen/", views.dokument_version_hochladen, name="version_hochladen"),
    path(
        "<int:pk>/version/<int:version_nr>/wiederherstellen/",
        views.dokument_version_wiederherstellen,
        name="version_wiederherstellen",
    ),

    # ---------------------------------------------------------------------------
    # Collabora Online Editor
    # ---------------------------------------------------------------------------
    path("<int:pk>/collabora/", views.collabora_editor, name="collabora"),

    # ---------------------------------------------------------------------------
    # WOPI-Protokoll (kein Login-Decorator – Collabora nutzt Token)
    # ---------------------------------------------------------------------------
    path("wopi/files/<int:pk>/", views.wopi_files_dispatch, name="wopi_files"),
    path("wopi/files/<int:pk>/contents/", views.wopi_contents_dispatch, name="wopi_contents"),
]
