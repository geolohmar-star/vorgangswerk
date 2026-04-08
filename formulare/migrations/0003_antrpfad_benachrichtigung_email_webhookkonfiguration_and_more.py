import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('formulare', '0002_antrpfad_workflow_template_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='antrpfad',
            name='benachrichtigung_email',
            field=models.EmailField(blank=True, default='', help_text='Bei neuem Antrag wird eine formatierte E-Mail an diese Adresse gesendet, z.B. hundesteuer@gemeinde.de', max_length=254, verbose_name='Benachrichtigungs-E-Mail'),
        ),
        # WebhookKonfiguration + WebhookZustellung already exist in DB (created in previous session)
        # Update Django state only, skip CREATE TABLE.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='WebhookKonfiguration',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(help_text="z.B. 'MACH-Anbindung Hundesteuer'", max_length=200, verbose_name='Bezeichnung')),
                        ('url', models.URLField(help_text='HTTPS-Endpunkt der empfangenden Anwendung', verbose_name='Ziel-URL')),
                        ('secret', models.CharField(help_text='Wird für HMAC-SHA256-Signatur verwendet (X-Webhook-Signature)', max_length=128, verbose_name='Signing-Secret')),
                        ('ereignisse', models.JSONField(default=list, help_text="Liste der Ereignisse, z.B. ['antrag.eingereicht']", verbose_name='Ereignisse')),
                        ('aktiv', models.BooleanField(default=True, verbose_name='Aktiv')),
                        ('erstellt_am', models.DateTimeField(auto_now_add=True)),
                        ('erstellt_von', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webhook_konfigurationen', to=settings.AUTH_USER_MODEL)),
                        ('pfad', models.ForeignKey(blank=True, help_text='Leer = gilt für alle Pfade', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='webhooks', to='formulare.antrpfad', verbose_name='Antragspfad')),
                    ],
                    options={
                        'verbose_name': 'Webhook-Konfiguration',
                        'verbose_name_plural': 'Webhook-Konfigurationen',
                        'ordering': ['name'],
                    },
                ),
                migrations.CreateModel(
                    name='WebhookZustellung',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('ereignis', models.CharField(max_length=50)),
                        ('payload_json', models.JSONField()),
                        ('versuche', models.IntegerField(default=0)),
                        ('letzter_status_code', models.IntegerField(blank=True, null=True)),
                        ('zugestellt_am', models.DateTimeField(blank=True, null=True)),
                        ('fehler', models.TextField(blank=True)),
                        ('erstellt_am', models.DateTimeField(auto_now_add=True)),
                        ('konfiguration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zustellungen', to='formulare.webhookkonfiguration')),
                    ],
                    options={
                        'verbose_name': 'Webhook-Zustellung',
                        'verbose_name_plural': 'Webhook-Zustellungen',
                        'ordering': ['-erstellt_am'],
                    },
                ),
            ],
        ),
    ]
