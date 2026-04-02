# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path

from . import views

app_name = "kommunikation"

urlpatterns = [
    # Postfach
    path("", views.postfach, name="postfach"),
    path("email/<int:pk>/", views.email_detail, name="email_detail"),
    path("anhang/<int:pk>/", views.anhang_download, name="anhang_download"),

    # Benachrichtigungen
    path("benachrichtigungen/", views.benachrichtigungen, name="benachrichtigungen"),
    path("benachrichtigungen/<int:pk>/gelesen/", views.benachrichtigung_gelesen, name="benachrichtigung_gelesen"),
    path("benachrichtigungen/alle-gelesen/", views.alle_gelesen, name="alle_gelesen"),
    path("benachrichtigungen/count/", views.benachrichtigungen_count, name="benachrichtigungen_count"),

    # HTMX-Partials
    path("navbar-badge/", views.navbar_badge, name="navbar_badge"),
]
