# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-01-13 08:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0012_add_levels'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('name', models.CharField(db_index=True, max_length=60, verbose_name='Label')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='registration',
            name='after_level',
            field=models.CharField(blank=True, choices=[('NP', 'NP'), ('1A', '1A'), ('1B', '1B'), ('1C', '1C'), ('2A', '2A'), ('2B', '2B'), ('2C', '2C'), ('3A', '3A'), ('3B', '3B'), ('3C', '3C'), ('4A', '4A'), ('4B', '4B'), ('4C', '4C'), ('5A', '5A'), ('5B', '5B'), ('5C', '5C'), ('6A', '6A'), ('6B', '6B'), ('6C', '6C'), ('7A', '7A'), ('7B', '7B'), ('7C', '7C')], max_length=5, verbose_name='End course level'),
        ),
        migrations.AddField(
            model_name='registration',
            name='transport',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='registrations.Transport', verbose_name='Transport information'),
        ),
    ]