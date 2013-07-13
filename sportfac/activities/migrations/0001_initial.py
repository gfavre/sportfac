# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Activity'
        db.create_table(u'activities_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50, db_index=True)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('image', self.gf('django.db.models.fields.files.ImageField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal(u'activities', ['Activity'])

        # Adding model 'Course'
        db.create_table(u'activities_course', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='courses', to=orm['activities.Activity'])),
            ('responsible', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['activities.Responsible'])),
            ('price', self.gf('django.db.models.fields.DecimalField')(max_digits=5, decimal_places=2)),
            ('number_of_sessions', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('day', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('start_date', self.gf('django.db.models.fields.DateField')()),
            ('end_date', self.gf('django.db.models.fields.DateField')()),
            ('start_time', self.gf('django.db.models.fields.TimeField')()),
            ('end_time', self.gf('django.db.models.fields.TimeField')()),
            ('place', self.gf('django.db.models.fields.TextField')()),
            ('min_participants', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('max_participants', self.gf('django.db.models.fields.PositiveSmallIntegerField')()),
            ('schoolyear_min', self.gf('django.db.models.fields.PositiveIntegerField')(default='1')),
            ('schoolyear_max', self.gf('django.db.models.fields.PositiveIntegerField')(default='6')),
        ))
        db.send_create_signal(u'activities', ['Course'])

        # Adding model 'Responsible'
        db.create_table(u'activities_responsible', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('first', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('last', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=14, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
        ))
        db.send_create_signal(u'activities', ['Responsible'])


    def backwards(self, orm):
        # Deleting model 'Activity'
        db.delete_table(u'activities_activity')

        # Deleting model 'Course'
        db.delete_table(u'activities_course')

        # Deleting model 'Responsible'
        db.delete_table(u'activities_responsible')


    models = {
        u'activities.activity': {
            'Meta': {'ordering': "['name']", 'object_name': 'Activity'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'activities.course': {
            'Meta': {'ordering': "['start_date', 'activity', 'day']", 'object_name': 'Course'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'courses'", 'to': u"orm['activities.Activity']"}),
            'day': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_participants': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'min_participants': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'number_of_sessions': ('django.db.models.fields.PositiveSmallIntegerField', [], {}),
            'place': ('django.db.models.fields.TextField', [], {}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '5', 'decimal_places': '2'}),
            'responsible': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activities.Responsible']"}),
            'schoolyear_max': ('django.db.models.fields.PositiveIntegerField', [], {'default': "'6'"}),
            'schoolyear_min': ('django.db.models.fields.PositiveIntegerField', [], {'default': "'1'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'start_time': ('django.db.models.fields.TimeField', [], {})
        },
        u'activities.responsible': {
            'Meta': {'ordering': "['last', 'first']", 'object_name': 'Responsible'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'})
        }
    }

    complete_apps = ['activities']