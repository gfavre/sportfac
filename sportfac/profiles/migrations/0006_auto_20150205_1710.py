# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0002_responsible_group'),
        ('profiles', '0005_auto_20150123_1438'),
    ]

    operations = [
        migrations.AlterField(
            model_name='child',
            name='birth_date',
            field=models.DateField(verbose_name='Birth date'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='child',
            name='first_name',
            field=models.CharField(max_length=50, verbose_name='First name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='child',
            name='last_name',
            field=models.CharField(max_length=50, verbose_name='Last name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='child',
            name='sex',
            field=models.CharField(max_length=1, verbose_name='Sex', choices=[(b'M', 'Male'), (b'F', 'Female')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='city',
            field=models.CharField(max_length=100, verbose_name='City', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone',
            field=models.CharField(max_length=30, verbose_name='Home phone', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone2',
            field=models.CharField(max_length=30, verbose_name='Mobile phone', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='private_phone3',
            field=models.CharField(max_length=30, verbose_name='Other phone', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='zipcode',
            field=models.PositiveIntegerField(verbose_name='NPA', blank=True),
            preserve_default=True,
        ),
    ]
