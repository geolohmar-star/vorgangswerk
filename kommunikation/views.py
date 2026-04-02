# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""kommunikation – Views: E-Mail-Postfach, Benachrichtigungen."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def postfach(request):
    """Eingehende E-Mails / Postfach-Uebersicht."""
    return render(request, "kommunikation/postfach.html")
