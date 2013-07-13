# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Course.number'
        db.add_column(u'activities_course', 'number',
                      self.gf('django.db.models.fields.IntegerField')(db_index=True, unique=True, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Activity.number'
        db.add_column(u'activities_activity', 'number',
                      self.gf('django.db.models.fields.IntegerField')(db_index=True, unique=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Course.number'
        db.delete_column(u'activities_course', 'number')

        # Deleting field 'Activity.number'
        db.delete_column(u'activities_activity', 'number')


    models = {
        u'activities.activity': {
            'Meta': {'ordering': "['name']", 'object_name': 'Activity'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
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
            'number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
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