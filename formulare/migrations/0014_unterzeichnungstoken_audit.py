from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("formulare", "0013_unterzeichnungstoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="unterzeichnungstoken",
            name="unterzeichnet_am",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Unterzeichnet am"),
        ),
        migrations.AddField(
            model_name="unterzeichnungstoken",
            name="unterzeichnet_ip",
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name="IP bei Unterzeichnung"),
        ),
    ]
