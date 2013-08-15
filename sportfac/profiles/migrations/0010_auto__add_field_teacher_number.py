# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Teacher.number'
        db.add_column(u'profiles_teacher', 'number',
                      self.gf('django.db.models.fields.IntegerField')(db_index=True, unique=True, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Teacher.number'
        db.delete_column(u'profiles_teacher', 'number')


    models = {
        u'activities.activity': {
            'Meta': {'ordering': "['name']", 'object_name': 'Activity'},
            'description': ('ckeditor.fields.RichTextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'informations': ('ckeditor.fields.RichTextField', [], {'blank': 'True'}),
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
            'schoolyear_max': ('django.db.models.fields.PositiveIntegerField', [], {'default': "'8'"}),
            'schoolyear_min': ('django.db.models.fields.PositiveIntegerField', [], {'default': "'1'"}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'start_time': ('django.db.models.fields.TimeField', [], {})
        },
        u'activities.extraneed': {
            'Meta': {'object_name': 'ExtraNeed'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'extra'", 'to': u"orm['activities.Activity']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question_label': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'activities.responsible': {
            'Meta': {'ordering': "['last', 'first']", 'object_name': 'Responsible'},
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'profiles.child': {
            'Meta': {'ordering': "('first_name',)", 'object_name': 'Child'},
            'birth_date': ('django.db.models.fields.DateField', [], {}),
            'courses': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['activities.Course']", 'through': u"orm['profiles.Registration']", 'symmetrical': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'family': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'children'", 'to': u"orm['profiles.FamilyUser']"}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'school_year': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profiles.SchoolYear']"}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'teacher': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'students'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['profiles.Teacher']"})
        },
        u'profiles.extrainfo': {
            'Meta': {'object_name': 'ExtraInfo'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['activities.ExtraNeed']"}),
            'registration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'extra_infos'", 'to': u"orm['profiles.Registration']"}),
            'value': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'profiles.familyuser': {
            'Meta': {'object_name': 'FamilyUser'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'country': ('django.db.models.fields.CharField', [], {'default': "u'Switzerland'", 'max_length': '100'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
            'finished_registration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_admin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'private_phone': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'private_phone2': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'private_phone3': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'profiles.registration': {
            'Meta': {'ordering': "('child__first_name', 'course__start_date')", 'unique_together': "(('course', 'child'),)", 'object_name': 'Registration'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profiles.Child']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participants'", 'to': u"orm['activities.Course']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'paid': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'validated': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'})
        },
        u'profiles.schoolyear': {
            'Meta': {'object_name': 'SchoolYear'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'year': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'})
        },
        u'profiles.teacher': {
            'Meta': {'ordering': "('last_name', 'first_name')", 'object_name': 'Teacher'},
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'db_index': 'True'}),
            'number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'years': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['profiles.SchoolYear']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['profiles']