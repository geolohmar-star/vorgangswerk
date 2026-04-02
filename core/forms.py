# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""core – Formulare: Benutzerprofil."""
from django import forms

from .models import Benutzerprofil


class BenutzerprofilForm(forms.ModelForm):
    """Formular zum Bearbeiten des eigenen Benutzerprofils."""

    class Meta:
        model = Benutzerprofil
        fields = ["abteilung", "telefon", "sprache"]
        widgets = {
            "abteilung": forms.TextInput(attrs={"class": "form-control"}),
            "telefon": forms.TextInput(attrs={"class": "form-control"}),
            "sprache": forms.Select(attrs={"class": "form-select"}),
        }
