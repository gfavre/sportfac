# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autoslug.fields
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0009_auto_20150220_2146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='description',
            field=ckeditor.fields.RichTextField(verbose_name='Description', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='informations',
            field=ckeditor.fields.RichTextField(help_text='Specific informations like outfit.', verbose_name='Informations', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='slug',
            field=autoslug.fields.AutoSlugField(help_text='Part of the url. Cannot contain punctuation, spaces or accentuated letters', unique=True, editable=False),
            preserve_default=True,
        ),
    ]
