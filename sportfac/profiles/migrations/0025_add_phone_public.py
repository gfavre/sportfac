from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0024_alter_schoolyear_year"),
    ]

    operations = [
        migrations.AddField(
            model_name="familyuser",
            name="phone_public",
            field=models.BooleanField(default=False, verbose_name="Phone visible for parents"),
        ),
    ]
