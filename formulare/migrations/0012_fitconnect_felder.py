from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formulare", "0011_bestaetigung_kontaktdaten"),
    ]

    operations = [
        migrations.AddField(
            model_name="antrpfad",
            name="fitconnect_destination_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="UUID der Empfangsbehörde (aus FITKO-Portal) für automatische OZG-Einreichung",
                max_length=100,
                verbose_name="FIT-Connect Destination-ID",
            ),
        ),
        migrations.AddField(
            model_name="antrsitzung",
            name="fitconnect_submission_id",
            field=models.CharField(
                blank=True,
                default="",
                max_length=100,
                verbose_name="FIT-Connect Submission-ID",
            ),
        ),
        migrations.AddField(
            model_name="antrsitzung",
            name="fitconnect_status",
            field=models.CharField(
                blank=True,
                default="",
                max_length=30,
                verbose_name="FIT-Connect Status",
            ),
        ),
    ]
