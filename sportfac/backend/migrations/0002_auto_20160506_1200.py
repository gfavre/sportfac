# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-05-06 10:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TenantPreferenceModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(blank=True, db_index=True, default=None, max_length=150, null=True)),
                ('name', models.CharField(db_index=True, max_length=150)),
                ('raw_value', models.TextField(blank=True, null=True)),
                ('instance', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='backend.YearTenant')),
            ],
            options={
                'abstract': False,
                'verbose_name': 'tenant preference',
                'verbose_name_plural': 'tenant preferences',
            },
        ),
        migrations.AlterUniqueTogether(
            name='tenantpreferencemodel',
            unique_together=set([('instance', 'section', 'name')]),
        ),
    ]