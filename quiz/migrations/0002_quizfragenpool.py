# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2026 Georg Klein
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quiz", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuizFragenPool",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="Name")),
                ("beschreibung", models.TextField(blank=True, verbose_name="Beschreibung")),
                ("fragen_json", models.JSONField(default=list, verbose_name="Fragen",
                    help_text="Liste von quizfrage-kompatiblen Dicts")),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("geaendert_am", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Quiz-Fragenpool",
                "verbose_name_plural": "Quiz-Fragenpools",
                "ordering": ["name"],
            },
        ),
    ]
