# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0004_registration_delete_validated_field'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='registration',
            options={'ordering': ('child__last_name', 'child__first_name', 'course__start_date'), 'verbose_name': 'Registration', 'verbose_name_plural': 'Registrations'},
        ),
        migrations.AlterModelOptions(
            name='schoolyear',
            options={'ordering': ('year',), 'verbose_name': 'School year', 'verbose_name_plural': 'School years'},
        ),
        migrations.AlterModelOptions(
            name='teacher',
            options={'ordering': ('last_name', 'first_name'), 'verbose_name': 'teacher', 'verbose_name_plural': 'teachers'},
        ),
        migrations.AlterField(
            model_name='child',
            name='sex',
            field=models.CharField(max_length=1, choices=[(b'M', 'Male'), (b'F', 'Female')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='address',
            field=models.TextField(verbose_name='Street', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='billing_identifier',
            field=models.CharField(max_length=45, verbose_name='Billing identifier', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='city',
            field=models.CharField(max_length=100, verbose_name='City'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='country',
            field=models.CharField(default='Switzerland', max_length=100, verbose_name='Country'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='date_joined',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='email',
            field=models.EmailField(unique=True, max_length=255, verbose_name='Email address', db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='finished_registration',
            field=models.BooleanField(default=False, help_text='For current year', verbose_name='Finished registration'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='first_name',
            field=models.CharField(max_length=30, verbose_name='First name', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='is_staff',
            field=models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name=b'staff status'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='last_name',
            field=models.CharField(max_length=30, verbose_name='Last name', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='paid',
            field=models.BooleanField(default=False, help_text='For current year', verbose_name='Has paid'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='familyuser',
            name='total',
            field=models.PositiveIntegerField(default=0, verbose_name='Total to be paid'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='registration',
            name='course',
            field=models.ForeignKey(related_name='participants', verbose_name='Course', to='activities.Course'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='schoolyear',
            name='year',
            field=models.PositiveIntegerField(unique=True, verbose_name='School year', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teacher',
            name='first_name',
            field=models.CharField(max_length=50, verbose_name='First name'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teacher',
            name='last_name',
            field=models.CharField(max_length=50, verbose_name='Last name', db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teacher',
            name='number',
            field=models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Number', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='teacher',
            name='years',
            field=models.ManyToManyField(to='profiles.SchoolYear', verbose_name='School years'),
            preserve_default=True,
        ),
    ]
