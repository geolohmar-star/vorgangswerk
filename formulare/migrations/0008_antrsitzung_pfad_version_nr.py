from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formulare", "0007_antrschritt_ist_aktion"),
    ]

    operations = [
        migrations.AddField(
            model_name="antrsitzung",
            name="pfad_version_nr",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name="Formular-Version",
                help_text="Version des Pfads zum Zeitpunkt des Starts (Audit/Rechtsschutz)",
            ),
        ),
    ]
