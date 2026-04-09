# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein

from django import forms
from .models import Organisation, Posteintrag


class PosteintragForm(forms.ModelForm):
    class Meta:
        model = Posteintrag
        fields = [
            "datum", "richtung", "typ",
            "absender_empfaenger", "betreff",
            "vorgang_bezug", "notiz", "dokument",
        ]
        widgets = {
            "datum":               forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "richtung":            forms.Select(attrs={"class": "form-select"}),
            "typ":                 forms.Select(attrs={"class": "form-select"}),
            "absender_empfaenger": forms.TextInput(attrs={"class": "form-control"}),
            "betreff":             forms.TextInput(attrs={"class": "form-control"}),
            "vorgang_bezug":       forms.TextInput(attrs={"class": "form-control"}),
            "notiz":               forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "dokument":            forms.Select(attrs={"class": "form-select"}),
        }


class OrganisationForm(forms.ModelForm):
    class Meta:
        model = Organisation
        fields = ["name", "typ", "email", "telefon", "fax", "strasse", "plz", "ort", "notiz"]
        widgets = {
            "name":    forms.TextInput(attrs={"class": "form-control"}),
            "typ":     forms.Select(attrs={"class": "form-select"}),
            "email":   forms.EmailInput(attrs={"class": "form-control"}),
            "telefon": forms.TextInput(attrs={"class": "form-control"}),
            "fax":     forms.TextInput(attrs={"class": "form-control"}),
            "strasse": forms.TextInput(attrs={"class": "form-control"}),
            "plz":     forms.TextInput(attrs={"class": "form-control"}),
            "ort":     forms.TextInput(attrs={"class": "form-control"}),
            "notiz":   forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
