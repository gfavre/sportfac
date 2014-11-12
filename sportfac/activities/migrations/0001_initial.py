# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import ckeditor.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50, verbose_name='Nom', db_index=True)),
                ('number', models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Num\xe9ro', blank=True)),
                ('slug', models.SlugField(help_text="Partie de l'URL. Ne peut contenit de ponctuation, d'espaces ou de caract\xe8res accentu\xe9s", unique=True)),
                ('informations', ckeditor.fields.RichTextField(help_text='Informations s\xe9pcifiques comme la tenue souhait\xe9e.', blank=True)),
                ('description', ckeditor.fields.RichTextField(blank=True)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'activit\xe9',
                'verbose_name_plural': 'activit\xe9s',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Num\xe9ro', blank=True)),
                ('uptodate', models.BooleanField(default=False, verbose_name='cours \xe0 jour')),
                ('price', models.DecimalField(verbose_name='Prix', max_digits=5, decimal_places=2)),
                ('number_of_sessions', models.PositiveSmallIntegerField(verbose_name='Nombre de sessions')),
                ('day', models.PositiveSmallIntegerField(verbose_name='Jour', choices=[(1, 'Lundi'), (2, 'Mardi'), (3, 'Mercredi'), (4, 'Jeudi'), (5, 'Vendredi'), (6, 'Samedi'), (7, 'Dimanche')])),
                ('start_date', models.DateField(verbose_name='Date de d\xe9but')),
                ('end_date', models.DateField(verbose_name='Date de fin')),
                ('start_time', models.TimeField(verbose_name='Heure de d\xe9but')),
                ('end_time', models.TimeField(verbose_name='Heure de fin')),
                ('place', models.TextField(verbose_name='Lieu')),
                ('min_participants', models.PositiveSmallIntegerField(verbose_name='Nombre minimum de participants')),
                ('max_participants', models.PositiveSmallIntegerField(verbose_name='Nombre maximum de participants')),
                ('schoolyear_min', models.PositiveIntegerField(default=b'1', verbose_name='Ann\xe9e scolaire minimale', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS')])),
                ('schoolyear_max', models.PositiveIntegerField(default=b'8', verbose_name='Ann\xe9e scolaire maximale', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS')])),
                ('activity', models.ForeignKey(related_name='courses', to='activities.Activity')),
            ],
            options={
                'ordering': ('activity__name', 'number'),
                'verbose_name': 'cours',
                'verbose_name_plural': 'cours',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtraNeed',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question_label', models.CharField(help_text='p. ex. Taille des chaussures?', max_length=255, verbose_name='Question')),
                ('activity', models.ForeignKey(related_name='extra', to='activities.Activity')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Responsible',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('first', models.CharField(help_text="Laissez ce champ vide dans le cas d'un nom d'entreprise", max_length=100, verbose_name='Pr\xe9nom', db_index=True, blank=True)),
                ('last', models.CharField(max_length=100, verbose_name='Nom', db_index=True)),
                ('phone', models.CharField(max_length=14, verbose_name='Num\xe9ro de t\xe9l\xe9phone', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='E-mail', blank=True)),
            ],
            options={
                'ordering': ['last', 'first'],
                'verbose_name': 'responsable',
                'verbose_name_plural': 'responsables',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='course',
            name='responsible',
            field=models.ForeignKey(verbose_name='Responsable', to='activities.Responsible'),
            preserve_default=True,
        ),
    ]
