# SPDX-License-Identifier: EUPL-1.2
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SicherungsProtokoll",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("typ", models.CharField(choices=[("datenbank","Datenbank (PostgreSQL)"),("dateien","Statische Dateien"),("komplett","Komplett")], max_length=20)),
                ("rhythmus", models.CharField(choices=[("taeglich","Täglich"),("woechentlich","Wöchentlich"),("monatlich","Monatlich"),("manuell","Manuell")], default="manuell", max_length=20)),
                ("status", models.CharField(choices=[("ok","Erfolgreich"),("fehler","Fehler"),("geprueft","Geprüft & OK")], default="ok", max_length=20)),
                ("dateiname", models.CharField(max_length=255)),
                ("dateipfad", models.CharField(max_length=500)),
                ("groesse_bytes", models.BigIntegerField(default=0)),
                ("sha256_pruefsumme", models.CharField(blank=True, max_length=64)),
                ("verschluesselt", models.BooleanField(default=True)),
                ("fehlermeldung", models.TextField(blank=True)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("geprueft_am", models.DateTimeField(blank=True, null=True)),
                ("geloescht_am", models.DateTimeField(blank=True, null=True)),
                ("erstellt_von", models.CharField(default="system", max_length=100)),
            ],
            options={"verbose_name": "Sicherungsprotokoll", "verbose_name_plural": "Sicherungsprotokolle", "ordering": ["-erstellt_am"]},
        ),
    ]
