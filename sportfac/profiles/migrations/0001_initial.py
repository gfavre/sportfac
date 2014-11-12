# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('activities', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FamilyUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('email', models.EmailField(unique=True, max_length=255, verbose_name='Email', db_index=True)),
                ('first_name', models.CharField(max_length=30, verbose_name='Pr\xe9nom', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='Nom', blank=True)),
                ('address', models.TextField(verbose_name='Rue', blank=True)),
                ('zipcode', models.PositiveIntegerField(verbose_name='NPA')),
                ('city', models.CharField(max_length=100, verbose_name='Commune')),
                ('country', models.CharField(default='Suisse', max_length=100, verbose_name='Pays')),
                ('private_phone', models.CharField(max_length=30, blank=True)),
                ('private_phone2', models.CharField(max_length=30, blank=True)),
                ('private_phone3', models.CharField(max_length=30, blank=True)),
                ('is_active', models.BooleanField(default=True, help_text=b'Designates whether this user should be treated as active. Unselect this instead of deleting accounts.')),
                ('is_admin', models.BooleanField(default=False)),
                ('is_staff', models.BooleanField(default=False, help_text="Indique si cet utilisateur peut se logguer dans la partie d'administration", verbose_name=b'staff status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name="Date d'inscription")),
                ('finished_registration', models.BooleanField(default=False, help_text="Pour l'ann\xe9e courante", verbose_name='Inscription termin\xe9e')),
                ('paid', models.BooleanField(default=False, help_text="Pour l'ann\xe9e courante", verbose_name='A pay\xe9')),
                ('billing_identifier', models.CharField(max_length=45, verbose_name='Identifiant de paiement', blank=True)),
                ('total', models.PositiveIntegerField(default=0, verbose_name='Total \xe0 payer')),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Child',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('sex', models.CharField(max_length=1, choices=[(b'M', 'Gar\xe7on'), (b'F', 'Fille')])),
                ('birth_date', models.DateField()),
            ],
            options={
                'ordering': ('last_name', 'first_name'),
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtraInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.CharField(max_length=255)),
                ('key', models.ForeignKey(to='activities.ExtraNeed')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(auto_now=True, db_index=True)),
                ('validated', models.BooleanField(default=False, db_index=True, verbose_name='Inscription confirm\xe9e')),
                ('child', models.ForeignKey(to='profiles.Child')),
                ('course', models.ForeignKey(related_name='participants', to='activities.Course')),
            ],
            options={
                'ordering': ('child__last_name', 'child__first_name', 'course__start_date'),
                'verbose_name': 'Inscription',
                'verbose_name_plural': 'Inscriptions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SchoolYear',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('year', models.PositiveIntegerField(unique=True, verbose_name='Ann\xe9e scolaire', choices=[(1, '1p HARMOS'), (2, '2p HARMOS'), (3, '3p HARMOS'), (4, '4p HARMOS'), (5, '5p HARMOS'), (6, '6p HARMOS'), (7, '7p HARMOS'), (8, '8p HARMOS')])),
            ],
            options={
                'ordering': ('year',),
                'verbose_name': 'Ann\xe9e scolaire',
                'verbose_name_plural': 'Ann\xe9es scolaires',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(db_index=True, unique=True, null=True, verbose_name='Num\xe9ro', blank=True)),
                ('first_name', models.CharField(max_length=50, verbose_name='Pr\xe9nom')),
                ('last_name', models.CharField(max_length=50, verbose_name='Nom', db_index=True)),
                ('years', models.ManyToManyField(to='profiles.SchoolYear', verbose_name='Ann\xe9es scolaires')),
            ],
            options={
                'ordering': ('last_name', 'first_name'),
                'verbose_name': 'enseignant',
                'verbose_name_plural': 'enseignants',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='registration',
            unique_together=set([('course', 'child')]),
        ),
        migrations.AddField(
            model_name='extrainfo',
            name='registration',
            field=models.ForeignKey(related_name='extra_infos', to='profiles.Registration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='child',
            name='courses',
            field=models.ManyToManyField(to='activities.Course', through='profiles.Registration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='child',
            name='family',
            field=models.ForeignKey(related_name='children', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='child',
            name='school_year',
            field=models.ForeignKey(to='profiles.SchoolYear'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='child',
            name='teacher',
            field=models.ForeignKey(related_name='students', on_delete=django.db.models.deletion.SET_NULL, to='profiles.Teacher', null=True),
            preserve_default=True,
        ),
    ]
