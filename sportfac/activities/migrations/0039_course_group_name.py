from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [("activities", "0038_auto_20260721_0709")]

    operations = [
        migrations.AddField(
            model_name="course",
            name="group_name",
            field=models.CharField(
                "Groupe",
                max_length=30,
                blank=True,
                default="",
                help_text="Numéro ou nom court porté par le moniteur, par exemple 3 ou Bleu. Commun à tous les inscrits du cours.",
            ),
        ),
    ]
