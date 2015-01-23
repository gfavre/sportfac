# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='informations',
            field=ckeditor.fields.RichTextField(help_text='Informations sp\xe9cifiques comme la tenue souhait\xe9e.', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='day',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Jour', choices=[(1, 'Lundi'), (2, 'Mardi'), (3, 'Mercredi'), (4, 'Jeudi'), (5, 'Vendredi'), (6, 'Samedi'), (7, 'Dimanche')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='number',
            field=models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Identifiant', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='course',
            name='responsible',
            field=models.ForeignKey(related_name='courses', verbose_name='Responsable', to='activities.Responsible'),
            preserve_default=True,
        ),
    ]
