# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Formulare fuer die Dokumente-App."""
from django import forms

from .models import Dokument, DokumentKategorie, DokumentTag


class DokumentHochladenForm(forms.Form):
    """Formular fuer den Upload eines neuen Dokuments."""

    datei = forms.FileField(
        label="Datei",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    titel = forms.CharField(
        label="Titel",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Leer = Dateiname"}),
        help_text="Leer lassen um den Dateinamen zu verwenden",
    )
    kategorie = forms.ModelChoiceField(
        label="Kategorie",
        queryset=DokumentKategorie.objects.all(),
        required=False,
        empty_label="– keine Kategorie –",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    tags = forms.ModelMultipleChoiceField(
        label="Tags",
        queryset=DokumentTag.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
    )


class DokumentBearbeitenForm(forms.ModelForm):
    """Formular fuer das Bearbeiten der Metadaten eines Dokuments."""

    class Meta:
        model = Dokument
        fields = ["titel", "kategorie", "tags", "gueltig_bis"]
        widgets = {
            "titel": forms.TextInput(attrs={"class": "form-control"}),
            "kategorie": forms.Select(attrs={"class": "form-select"}),
            "tags": forms.SelectMultiple(attrs={"class": "form-select", "size": "4"}),
            "gueltig_bis": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
