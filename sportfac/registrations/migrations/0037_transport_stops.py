import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("registrations", "0036_transport_bib_prefix"),
        ("activities", "0039_course_group_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="transport",
            name="stop_question",
            field=models.ForeignKey(
                to="activities.extraneed",
                verbose_name="Question sur l’arrêt",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="transport",
            name="stop_values",
            field=models.JSONField("Arrêts desservis", default=list, blank=True),
        ),
    ]
