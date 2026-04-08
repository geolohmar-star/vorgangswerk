# SPDX-License-Identifier: EUPL-1.2
# Generated manually
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PortalAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credits", models.IntegerField(default=0)),
                ("stripe_customer_id", models.CharField(blank=True, max_length=100)),
                ("email_verifiziert", models.BooleanField(default=False)),
                ("verifikations_token", models.CharField(blank=True, max_length=64)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portal_account",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Portal-Konto",
                "verbose_name_plural": "Portal-Konten",
            },
        ),
        migrations.CreateModel(
            name="FormularAnalyse",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dateiname", models.CharField(max_length=255)),
                ("pdf_inhalt", models.BinaryField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("wartend", "Wartend"),
                            ("verarbeitung", "In Verarbeitung"),
                            ("fertig", "Fertig"),
                            ("fehler", "Fehler"),
                            ("importiert", "Importiert"),
                        ],
                        default="wartend",
                        max_length=20,
                    ),
                ),
                ("ergebnis_json", models.JSONField(blank=True, null=True)),
                ("fehler_meldung", models.TextField(blank=True)),
                ("credits_verbraucht", models.IntegerField(default=1)),
                ("importierter_pfad_pk", models.IntegerField(blank=True, null=True)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("fertig_am", models.DateTimeField(blank=True, null=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysen",
                        to="portal.portalaccount",
                    ),
                ),
            ],
            options={
                "verbose_name": "Formular-Analyse",
                "verbose_name_plural": "Formular-Analysen",
                "ordering": ["-erstellt_am"],
            },
        ),
        migrations.CreateModel(
            name="CreditTransaktion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "typ",
                    models.CharField(
                        choices=[
                            ("kauf", "Kauf"),
                            ("verbrauch", "Verbrauch"),
                            ("rueckerstattung", "Rückerstattung"),
                        ],
                        max_length=20,
                    ),
                ),
                ("betrag", models.IntegerField()),
                ("beschreibung", models.TextField(blank=True)),
                ("stripe_payment_intent", models.CharField(blank=True, max_length=100)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transaktionen",
                        to="portal.portalaccount",
                    ),
                ),
            ],
            options={
                "verbose_name": "Credit-Transaktion",
                "verbose_name_plural": "Credit-Transaktionen",
                "ordering": ["-erstellt_am"],
            },
        ),
    ]
