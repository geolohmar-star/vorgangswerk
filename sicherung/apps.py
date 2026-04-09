# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.apps import AppConfig


class SicherungConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sicherung"
    verbose_name = "Datensicherung"
