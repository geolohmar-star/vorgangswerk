# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""formulare – Views: Formular-Editor, Ausfuellen, Auswertung."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def formular_liste(request):
    """Liste aller Formulare / Pfade."""
    return render(request, "formulare/liste.html")
