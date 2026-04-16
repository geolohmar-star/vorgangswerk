from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formulare', '0005_antrschritt_loop_bezeichnung'),
    ]

    operations = [
        migrations.AddField(
            model_name='antrschritt',
            name='pdf_gruppe',
            field=models.CharField(
                blank=True, default='',
                help_text="Gruppenname für PDF und JSON-Export, z.B. 'Persönliche Daten', 'Wohnort'",
                max_length=100,
                verbose_name='PDF-Gruppe',
            ),
        ),
    ]
