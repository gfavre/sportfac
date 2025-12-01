from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("activities", "0035_auto_20251201_1136"),
    ]

    operations = [
        # 1) Remove the incorrect constraint
        migrations.RemoveConstraint(
            model_name="coursesinstructors",
            name="unique_instructor_function_single_contract_number",
        ),

        # 2) Add the correct one: contract_number must be unique *per instructor + function*,
        #    but can appear on several CI rows (correct business rule)
        migrations.AddConstraint(
            model_name="coursesinstructors",
            constraint=models.UniqueConstraint(
                fields=["instructor", "function", "contract_number"],
                name="unique_instructor_function_contract_number",
            ),
        ),
    ]