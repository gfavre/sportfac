# Generated by Django 3.2.25 on 2024-10-08 14:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wizard', '0003_wizardstep_subtitle'),
    ]

    operations = [
        migrations.AddField(
            model_name='wizardstep',
            name='link_display',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]