from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0002_einladung'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Einladung',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('token', models.CharField(blank=True, max_length=64, unique=True)),
                ('start_credits', models.IntegerField(default=0, help_text='Credits die dem neuen Konto gutgeschrieben werden')),
                ('erstellt_am', models.DateTimeField(auto_now_add=True)),
                ('gueltig_bis', models.DateTimeField(blank=True, null=True)),
                ('eingeloest_am', models.DateTimeField(blank=True, null=True)),
                ('notiz', models.TextField(blank=True, help_text='Interne Notiz (nicht sichtbar für Eingeladene)')),
                ('eingeloest_von', models.OneToOneField(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='einladung',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Einladung',
                'verbose_name_plural': 'Einladungen',
                'ordering': ['-erstellt_am'],
            },
        ),
    ]
