# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-09-06 11:32
from __future__ import unicode_literals

from django.db import migrations, models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0006_school_selectable'),
    ]

    operations = [
        migrations.AlterField(
            model_name='familyuser',
            name='is_active',
            field=models.BooleanField(default=True, help_text=b'Designates whether this user should be treated as active.'),
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=30, verbose_name='Home phone'),
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone2',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=30, verbose_name='Mobile phone'),
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone3',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=30, verbose_name='Other phone'),
        ),
    ]