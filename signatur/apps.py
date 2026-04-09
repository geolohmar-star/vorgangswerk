# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.apps import AppConfig


class SignaturConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "signatur"
    verbose_name = "Digitale Signatur"

    def ready(self):
        import signatur.signals  # noqa: F401
