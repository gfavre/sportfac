from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0035_registration_reg_child_status_idx")]

    operations = [
        migrations.AddField(
            model_name="transport",
            name="bib_prefix",
            field=models.PositiveIntegerField("Préfixe des dossards", null=True, blank=True, unique=True),
        ),
    ]
