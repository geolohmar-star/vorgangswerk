# SPDX-License-Identifier: EUPL-1.2
from django.urls import path
from . import views

app_name = "sicherung"

urlpatterns = [
    path("", views.uebersicht, name="uebersicht"),
    path("starten/", views.sicherung_starten, name="starten"),
    path("<int:pk>/pruefen/", views.integritaet_pruefen, name="pruefen"),
    path("<int:pk>/wiederherstellen/", views.wiederherstellen, name="wiederherstellen"),
]
