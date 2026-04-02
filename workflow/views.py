# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""workflow – Views: Workflow-Editor, Engine, Team-Queues."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def workflow_liste(request):
    """Liste aller Workflow-Definitionen."""
    return render(request, "workflow/liste.html")
