# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""dokumente – Views: Collabora WOPI, Vorlagen, Bescheide, PDF."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dokument_liste(request):
    """Liste aller Dokumente."""
    return render(request, "dokumente/liste.html")
