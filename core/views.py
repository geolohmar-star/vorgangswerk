# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""core – Views: Dashboard, Benutzerverwaltung."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    """Startseite nach dem Login."""
    return render(request, "core/dashboard.html")
