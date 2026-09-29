from django.core.validators import URLValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0011_alter_datatranstransaction_transaction_id")]

    operations = [
        migrations.AlterField(
            model_name="postfinancetransaction",
            name="payment_page_url",
            field=models.TextField(blank=True, null=True, validators=[URLValidator()]),
        ),
    ]
