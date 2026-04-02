# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Vorgangswerk – URL-Konfiguration."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

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

    # ---------------------------------------------------------------------------
    # Apps
    # ---------------------------------------------------------------------------
    path("", include("core.urls")),
    path("formulare/", include("formulare.urls")),
    path("antrag/", include(("formulare.public_urls", "formulare_pub"))),
    path("workflow/", include("workflow.urls")),
    path("dokumente/", include("dokumente.urls")),
    path("kommunikation/", include("kommunikation.urls")),
]
