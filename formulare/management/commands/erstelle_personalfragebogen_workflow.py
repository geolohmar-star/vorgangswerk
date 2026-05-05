"""
Erstellt den Workflow-Template für den Personalfragebogen-Prozess:
  1. Sachbearbeiter ergänzt Felder
  2. Arbeitgeber-Signatur
  3. Arbeitnehmer-Signatur
  4. DATEV-Export / Abschluss
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Erstellt Workflow-Template für Personalfragebogen"

    def handle(self, *args, **options):
        from workflow.models import WorkflowTemplate, WorkflowStep, WorkflowTransition

        name = "Personalfragebogen – HR-Onboarding"

        if WorkflowTemplate.objects.filter(name=name).exists():
            self.stdout.write(self.style.WARNING(f'Vorlage "{name}" existiert bereits – übersprungen.'))
            return

        admin = User.objects.filter(is_superuser=True).first()

        template = WorkflowTemplate.objects.create(
            name=name,
            beschreibung=(
                "Vollständiger HR-Onboarding-Ablauf: "
                "Sachbearbeiter ergänzt interne Felder → "
                "Arbeitgeber signiert → Arbeitnehmer signiert → DATEV-Export."
            ),
            kategorie="bearbeitung",
            ist_aktiv=True,
            ist_graph_workflow=True,
            trigger_event="personalfragebogen_abgeschlossen",
            erstellt_von=admin,
        )

        s1 = WorkflowStep.objects.create(
            template=template,
            titel="Sachbearbeiter-Nacherfassung",
            beschreibung=(
                "Bitte ergänzen Sie die internen HR-Felder (Steuerklasse, "
                "Krankenkasse, Betriebsstätte, Entlohnung usw.) über den Button "
                "«Sachbearbeiter-Felder ergänzen» oben rechts. "
                "Danach Task als erledigt markieren."
            ),
            schritt_typ="task",
            aktion_typ="bearbeiten",
            reihenfolge=1,
            node_id="s1",
            pos_x=100,
            pos_y=100,
            frist_tage=2,
            zustaendig_rolle="gruppe",
        )

        s2 = WorkflowStep.objects.create(
            template=template,
            titel="Arbeitgeber signiert",
            beschreibung=(
                "Senden Sie die Signaturanfrage an den Arbeitgeber über den "
                "PDF-Download. Nach erfolgter Unterschrift Task als erledigt markieren."
            ),
            schritt_typ="task",
            aktion_typ="genehmigen",
            reihenfolge=2,
            node_id="s2",
            pos_x=300,
            pos_y=100,
            frist_tage=3,
            zustaendig_rolle="gruppe",
        )

        s3 = WorkflowStep.objects.create(
            template=template,
            titel="Arbeitnehmer signiert",
            beschreibung=(
                "Senden Sie die Signaturanfrage an den Arbeitnehmer. "
                "Nach erfolgter Unterschrift Task als erledigt markieren."
            ),
            schritt_typ="task",
            aktion_typ="genehmigen",
            reihenfolge=3,
            node_id="s3",
            pos_x=500,
            pos_y=100,
            frist_tage=3,
            zustaendig_rolle="gruppe",
        )

        s4 = WorkflowStep.objects.create(
            template=template,
            titel="DATEV-Export & Abschluss",
            beschreibung=(
                "Alle Signaturen liegen vor. Exportieren Sie die Daten via "
                "«DATEV LODAS herunterladen» oder «DATEV HR:Exchange». "
                "Danach Vorgang abschliessen."
            ),
            schritt_typ="task",
            aktion_typ="bearbeiten",
            reihenfolge=4,
            node_id="s4",
            pos_x=700,
            pos_y=100,
            frist_tage=1,
            zustaendig_rolle="gruppe",
        )

        WorkflowTransition.objects.create(
            template=template, von_schritt=s1, zu_schritt=s2,
            bedingung_typ="immer", label="erledigt", prioritaet=1,
        )
        WorkflowTransition.objects.create(
            template=template, von_schritt=s2, zu_schritt=s3,
            bedingung_typ="immer", label="signiert", prioritaet=1,
        )
        WorkflowTransition.objects.create(
            template=template, von_schritt=s3, zu_schritt=s4,
            bedingung_typ="immer", label="signiert", prioritaet=1,
        )
        WorkflowTransition.objects.create(
            template=template, von_schritt=s4, zu_schritt=None,
            bedingung_typ="immer", label="abgeschlossen", prioritaet=1,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Workflow-Template "{name}" (ID {template.pk}) erfolgreich angelegt.\n'
            f'Jetzt im Formular-Editor beim Personalfragebogen unter '
            f'Einstellungen → Workflow → "{name}" auswählen.'
        ))
