# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("formulare", "0004_antrpfad_leika_schluessel"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuizErgebnis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("sitzung", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="quiz_ergebnis",
                    to="formulare.antrsitzung",
                )),
                ("punkte_erreicht", models.DecimalField(decimal_places=2, max_digits=8)),
                ("punkte_gesamt", models.DecimalField(decimal_places=2, max_digits=8)),
                ("fehlerpunkte", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("prozent", models.DecimalField(decimal_places=2, max_digits=5)),
                ("bestanden", models.BooleanField()),
                ("note", models.CharField(blank=True, max_length=10)),
                ("note_text", models.CharField(blank=True, max_length=40)),
                ("bewertungsmodell", models.CharField(max_length=20)),
                ("antworten_json", models.JSONField(default=dict)),
                ("config_snapshot", models.JSONField(default=dict)),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Quiz-Ergebnis",
                "verbose_name_plural": "Quiz-Ergebnisse",
                "ordering": ["-erstellt_am"],
            },
        ),
        migrations.CreateModel(
            name="QuizZertifikat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ergebnis", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="zertifikat",
                    to="quiz.quizergebnis",
                )),
                ("pdf_inhalt", models.BinaryField()),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("ablaufdatum", models.DateField(blank=True, null=True)),
                ("erinnerung_gesendet", models.BooleanField(default=False)),
            ],
            options={
                "verbose_name": "Quiz-Zertifikat",
                "verbose_name_plural": "Quiz-Zertifikate",
            },
        ),
    ]
