# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
"""Formulare fuer die Workflow-App."""
from django import forms

from .models import ProzessAntrag, WorkflowTrigger


class ProzessAntragForm(forms.ModelForm):
    """Formular fuer das Einreichen eines neuen Prozessantrags."""

    schritte = forms.CharField(
        label="Prozessschritte",
        widget=forms.Textarea(attrs={"rows": 5, "class": "form-control"}),
        required=False,
        help_text=(
            "Beschreibe die Schritte des Prozesses (einer pro Zeile). "
            "Z.B. '1. Antragsteller faellt Beleg aus', '2. Vorgesetzter prueft'."
        ),
    )

    class Meta:
        model = ProzessAntrag
        fields = [
            "name",
            "ziel",
            "ausloeser_typ",
            "ausloeser_detail",
            "schritte",
            "pdf_benoetigt",
            "team_benoetigt",
            "team_vorschlag",
            "bemerkungen",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "ziel": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "ausloeser_typ": forms.Select(attrs={"class": "form-select"}),
            "ausloeser_detail": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "team_vorschlag": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "bemerkungen": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
        }

    def clean_schritte(self):
        """Konvertiert mehrzeiligen Text in eine JSON-Liste."""
        text = self.cleaned_data.get("schritte", "")
        zeilen = [z.strip() for z in text.splitlines() if z.strip()]
        return zeilen


class WorkflowTriggerForm(forms.ModelForm):
    """Formular fuer das Anlegen und Bearbeiten von Workflow-Triggern."""

    class Meta:
        model = WorkflowTrigger
        fields = [
            "name",
            "beschreibung",
            "trigger_event",
            "trigger_auf",
            "content_type",
            "ist_aktiv",
            "antragsteller_pfad",
            "workflow_instance_feld",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "beschreibung": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "trigger_event": forms.TextInput(attrs={"class": "form-control"}),
            "trigger_auf": forms.Select(attrs={"class": "form-select"}),
            "content_type": forms.Select(attrs={"class": "form-select"}),
            "antragsteller_pfad": forms.TextInput(attrs={"class": "form-control"}),
            "workflow_instance_feld": forms.TextInput(attrs={"class": "form-control"}),
        }
