# Manuell erstellt – pdf_original war bereits in der DB vorhanden, daher gefakt
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portal', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='formularanalyse',
            name='pdf_original',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]
