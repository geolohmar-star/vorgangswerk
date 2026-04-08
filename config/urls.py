# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Vorgangswerk – URL-Konfiguration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from core.api import api

urlpatterns = [
    # ---------------------------------------------------------------------------
    # Admin
    # ---------------------------------------------------------------------------
    path("admin/", admin.site.urls),

    # ---------------------------------------------------------------------------
    # Auth (Login / Logout)
    # ---------------------------------------------------------------------------
    path("auth/login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("auth/logout/", auth_views.LogoutView.as_view(), name="logout"),
    # Django-Standard-Login-URL auf unsere Login-Seite weiterleiten
    path("accounts/login/", RedirectView.as_view(url="/auth/login/", query_string=True)),

    # ---------------------------------------------------------------------------
    # Apps
    # ---------------------------------------------------------------------------
    path("api/", api.urls),
    path("", include("core.urls")),
    path("formulare/", include("formulare.urls")),
    path("antrag/", include(("formulare.public_urls", "formulare_pub"))),
    path("vorgang/", include(("formulare.tracking_urls", "formulare_tracking"))),
    path("workflow/", include("workflow.urls")),
    path("dokumente/", include("dokumente.urls")),
    path("kommunikation/", include("kommunikation.urls")),
    path("korrespondenz/", include("korrespondenz.urls")),
    path("signatur/", include("signatur.urls")),
    path("portal/", include(("portal.urls", "portal"))),
    path("sicherung/", include(("sicherung.urls", "sicherung"))),
    path("postbuch/", include(("post.urls", "post"))),
    path("quiz/", include(("quiz.urls", "quiz"))),
]
