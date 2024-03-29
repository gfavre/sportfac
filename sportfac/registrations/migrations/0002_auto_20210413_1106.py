# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-04-13 09:06
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registrations", "0001_squashed_0037_auto_20200812_1403"),
    ]

    operations = [
        migrations.AddField(
            model_name="bill",
            name="payment_method",
            field=models.CharField(blank=True, max_length=20, verbose_name="Payment method"),
        ),
        migrations.AlterField(
            model_name="childactivitylevel",
            name="after_level",
            field=models.CharField(
                blank=True,
                choices=[
                    ("NP", "NP"),
                    ("CM", "CM"),
                    ("ABS", "ABS"),
                    ("NPA", "NPA"),
                    ("NPB", "NPB"),
                    ("NPC", "NPC"),
                    ("A 1A", "A 1A"),
                    ("A 1B", "A 1B"),
                    ("A 1C", "1C"),
                    ("A 2A", "2A"),
                    ("A 2B", "A 2B"),
                    ("A 2C", "A 2C"),
                    ("A 3A", "A 3A"),
                    ("A 3B", "A 3B"),
                    ("A 3C", "A 3C"),
                    ("A 4A", "A 4A"),
                    ("A 4B", "A 4B"),
                    ("A 4C", "A 4C"),
                    ("A 5A", "A 5A"),
                    ("A 5B", "A 5B"),
                    ("A 5C", "A 5C"),
                    ("A 6A", "A 6A"),
                    ("A 6B", "A 6B"),
                    ("A 6C", "A 6C"),
                    ("A 7A", "A 7A"),
                    ("A 7B", "A 7B"),
                    ("A 7C", "A 7C"),
                    ("S 1A", "S 1A"),
                    ("S 1B", "S 1B"),
                    ("S 1C", "S 1C"),
                    ("S 2A", "S 2A"),
                    ("S 2B", "S 2B"),
                    ("S 2C", "S 2C"),
                    ("S 3A", "S 3A"),
                    ("S 3B", "S 3B"),
                    ("S 3C", "S 3C"),
                    ("S 4A", "S 4A"),
                    ("S 4B", "S 4B"),
                    ("S 4C", "S 4C"),
                    ("S 5A", "S 5A"),
                    ("S 5B", "S 5B"),
                    ("S 5C", "S 5C"),
                    ("S 6A", "S 6A"),
                    ("S 6B", "S 6B"),
                    ("S 6C", "S 6C"),
                    ("S 7A", "S 7A"),
                    ("S 7B", "S 7B"),
                    ("S 7C", "S 7C"),
                ],
                max_length=5,
                verbose_name="End course level",
            ),
        ),
    ]
