# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Audit-Signale: Login, Logout, fehlgeschlagene Anmeldung."""
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver


def _ip(request):
    if not request:
        return None
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    return ip or request.META.get("REMOTE_ADDR") or None


@receiver(user_logged_in)
def bei_login(sender, request, user, **kwargs):
    from core.models import AuditLog
    AuditLog.objects.create(
        user=user,
        aktion="login",
        beschreibung=f"Erfolgreiche Anmeldung: {user.username}",
        app="core",
        ip_adresse=_ip(request),
    )


@receiver(user_logged_out)
def bei_logout(sender, request, user, **kwargs):
    from core.models import AuditLog
    AuditLog.objects.create(
        user=user,
        aktion="logout",
        beschreibung=f"Abmeldung: {user.username if user else 'unbekannt'}",
        app="core",
        ip_adresse=_ip(request),
    )


@receiver(user_login_failed)
def bei_login_fehlgeschlagen(sender, credentials, request, **kwargs):
    from core.models import AuditLog
    username = credentials.get("username", "?")
    AuditLog.objects.create(
        user=None,
        aktion="login_fehlgeschlagen",
        beschreibung=f"Fehlgeschlagener Login-Versuch für: {username}",
        app="core",
        ip_adresse=_ip(request),
    )
