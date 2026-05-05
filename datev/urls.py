# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "datev"

urlpatterns = [
    path("connect/",                          views.datev_connect,     name="connect"),
    path("callback/",                         views.datev_callback,    name="callback"),
    path("status/",                           views.datev_status,      name="status"),
    path("trennen/",                          views.datev_trennen,     name="trennen"),
    path("uebertragen/<int:sitzung_pk>/",      views.datev_uebertragen,      name="uebertragen"),
    path("lodas/<int:sitzung_pk>/download/",  views.datev_lodas_download,   name="lodas_download"),
    path("lodas/<int:sitzung_pk>/hochladen/",     views.datev_lodas_hochladen,   name="lodas_hochladen"),
    path("lodas/<int:sitzung_pk>/steuerberater/", views.datev_an_steuerberater,  name="an_steuerberater"),
]
