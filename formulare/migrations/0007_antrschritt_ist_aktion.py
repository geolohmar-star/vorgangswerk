from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formulare", "0006_antrschritt_pdf_gruppe"),
    ]

    operations = [
        migrations.AddField(
            model_name="antrschritt",
            name="ist_aktion",
            field=models.BooleanField(
                default=False,
                verbose_name="Aktions-Schritt",
                help_text="Wird automatisch ausgeführt – unsichtbar für den Antragsteller",
            ),
        ),
    ]
