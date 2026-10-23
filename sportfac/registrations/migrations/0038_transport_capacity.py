from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [("registrations", "0037_transport_stops")]

    operations = [
        migrations.AddField(
            model_name="transport",
            name="capacity",
            field=models.PositiveIntegerField("Nombre de places", null=True, blank=True),
        ),
    ]
