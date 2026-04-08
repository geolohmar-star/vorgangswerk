from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formulare', '0003_antrpfad_benachrichtigung_email_webhookkonfiguration_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='antrpfad',
            name='leika_schluessel',
            field=models.CharField(
                blank=True,
                default='',
                help_text='14-stellige LeiKa-Leistungsnummer, z.B. 99108018026000 (Hundesteuer-Anmeldung)',
                max_length=20,
                verbose_name='LeiKa-Schlüssel',
            ),
        ),
    ]
