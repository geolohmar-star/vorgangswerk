from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("formulare", "0012_fitconnect_felder"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnterzeichnungsToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(db_index=True, max_length=64, unique=True)),
                ("feld_id", models.CharField(max_length=100, verbose_name="Feld-ID (signatur)")),
                ("empfaenger_email", models.EmailField(verbose_name="E-Mail des Unterzeichners")),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("abgelaufen_am", models.DateTimeField(verbose_name="Gültig bis")),
                ("verwendet", models.BooleanField(default=False, verbose_name="Bereits verwendet")),
                (
                    "sitzung",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="unterzeichnungs_token",
                        to="formulare.antrsitzung",
                    ),
                ),
            ],
            options={
                "verbose_name": "Unterzeichnungs-Token",
                "verbose_name_plural": "Unterzeichnungs-Token",
                "ordering": ["-erstellt_am"],
            },
        ),
    ]
