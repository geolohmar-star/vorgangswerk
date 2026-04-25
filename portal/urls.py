# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    # Auth
    path("", views.dashboard, name="index"),
    path("registrierung/<str:token>/", views.registrierung, name="registrierung"),
    path("login/", views.portal_login, name="login"),
    path("logout/", views.portal_logout, name="logout"),
    path("verifizieren/<str:token>/", views.email_verifizieren, name="email_verifizieren"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),
    path("verwaltung/", views.admin_verwaltung, name="admin_verwaltung"),

    # Upload & Analyse
    path("upload/", views.upload, name="upload"),
    path("analyse/<int:pk>/", views.analyse_detail, name="analyse_detail"),
    path("analyse/<int:pk>/status.json", views.analyse_status_json, name="analyse_status_json"),
    path("analyse/<int:pk>/importieren/", views.analyse_importieren, name="analyse_importieren"),
    path("analyse/<int:pk>/pruefen/", views.analyse_pruefen, name="analyse_pruefen"),
    path("analyse/<int:pk>/pdf/", views.analyse_pdf, name="analyse_pdf"),
    path("analyse/<int:pk>/original-pdf-upload/", views.analyse_original_pdf_upload, name="analyse_original_pdf_upload"),
    path("analyse/<int:pk>/diagnose-pdf/", views.analyse_diagnose_pdf, name="analyse_diagnose_pdf"),
    path("analyse/<int:pk>/seite/<int:seite_nr>.png", views.analyse_seite_png, name="analyse_seite_png"),
    path("analyse/<int:pk>/felder.json", views.analyse_felder_json, name="analyse_felder_json"),
    path("analyse/<int:pk>/koordinaten/", views.analyse_koordinaten_speichern, name="analyse_koordinaten_speichern"),

    # Credits
    path("credits/", views.credits_kaufen, name="credits_kaufen"),
    path("credits/checkout/<str:paket_id>/", views.checkout_starten, name="checkout_starten"),
    path("credits/erfolg/", views.credits_erfolg, name="credits_erfolg"),

    # Stripe Webhook (kein CSRF)
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
