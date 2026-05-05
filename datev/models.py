# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.db import models
from django.contrib.auth.models import User


class DatevToken(models.Model):
    """Speichert OAuth2-Tokens für einen DATEV-Mandanten (pro Benutzer)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="datev_token")
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True)
    token_type = models.CharField(max_length=50, default="Bearer")
    expires_at = models.DateTimeField(null=True, blank=True)
    scope = models.TextField(blank=True)
    # DATEV-spezifisch
    consultant_number = models.CharField(max_length=50, blank=True, verbose_name="Beraternummer")
    client_number = models.CharField(max_length=50, blank=True, verbose_name="Mandantennummer")
    erstellt_am = models.DateTimeField(auto_now_add=True)
    aktualisiert_am = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "DATEV Token"
        verbose_name_plural = "DATEV Tokens"

    def __str__(self):
        return f"DATEV Token – {self.user.username}"

    def ist_abgelaufen(self):
        from django.utils import timezone
        if not self.expires_at:
            return False
        return timezone.now() >= self.expires_at
