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
            name="DatevToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("access_token", models.TextField()),
                ("refresh_token", models.TextField(blank=True)),
                ("token_type", models.CharField(default="Bearer", max_length=50)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("scope", models.TextField(blank=True)),
                ("consultant_number", models.CharField(blank=True, max_length=50, verbose_name="Beraternummer")),
                ("client_number", models.CharField(blank=True, max_length=50, verbose_name="Mandantennummer")),
                ("erstellt_am", models.DateTimeField(auto_now_add=True)),
                ("aktualisiert_am", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="datev_token",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "DATEV Token",
                "verbose_name_plural": "DATEV Tokens",
            },
        ),
    ]
