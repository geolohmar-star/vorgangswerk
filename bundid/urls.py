# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

urlpatterns = [
    path("login/",    views.bundid_login,    name="login"),
    path("acs/",      views.bundid_acs,      name="acs"),
    path("metadata/", views.bundid_metadata, name="metadata"),
]
