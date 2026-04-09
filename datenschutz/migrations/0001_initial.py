# SPDX-License-Identifier: EUPL-1.2
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Loeschprotokoll",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id_intern", models.IntegerField(help_text="PK des gelöschten Django-Users – kein FK mehr.", verbose_name="Interne User-ID (war)")),
                ("benutzername_kuerzel", models.CharField(help_text="Erste 5 Zeichen des Benutzernamens zur Identifikation.", max_length=10, verbose_name="Benutzername-Kürzel")),
                ("email_kuerzel", models.CharField(blank=True, help_text="Erste 3 Zeichen + Domain-Teil der E-Mail.", max_length=20, verbose_name="E-Mail-Kürzel")),
                ("loeschung_ausgefuehrt_am", models.DateTimeField(default=django.utils.timezone.now)),
                ("loeschung_durch", models.CharField(max_length=200, verbose_name="Ausgeführt durch")),
                ("kategorien", models.JSONField(default=dict, help_text="Dict: Kategoriename → Anzahl Datensätze.", verbose_name="Gelöschte Datenkategorien")),
                ("protokoll_pdf", models.BinaryField(blank=True, null=True, verbose_name="Protokoll-PDF")),
            ],
            options={
                "verbose_name": "Löschprotokoll",
                "verbose_name_plural": "Löschprotokolle",
                "ordering": ["-loeschung_ausgefuehrt_am"],
            },
        ),
    ]
