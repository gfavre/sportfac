# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'FamilyUser'
        db.create_table(u'profiles_familyuser', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('last_login', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('is_superuser', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=255, db_index=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('address', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('zipcode', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('country', self.gf('django.db.models.fields.CharField')(default=u'Switzerland', max_length=100)),
            ('private_phone', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('private_phone2', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('is_admin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_staff', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('date_joined', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'profiles', ['FamilyUser'])

        # Adding M2M table for field groups on 'FamilyUser'
        db.create_table(u'profiles_familyuser_groups', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('familyuser', models.ForeignKey(orm[u'profiles.familyuser'], null=False)),
            ('group', models.ForeignKey(orm[u'auth.group'], null=False))
        ))
        db.create_unique(u'profiles_familyuser_groups', ['familyuser_id', 'group_id'])

        # Adding M2M table for field user_permissions on 'FamilyUser'
        db.create_table(u'profiles_familyuser_user_permissions', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('familyuser', models.ForeignKey(orm[u'profiles.familyuser'], null=False)),
            ('permission', models.ForeignKey(orm[u'auth.permission'], null=False))
        ))
        db.create_unique(u'profiles_familyuser_user_permissions', ['familyuser_id', 'permission_id'])

        # Adding model 'Child'
        db.create_table(u'profiles_child', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('sex', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('birth_date', self.gf('django.db.models.fields.DateField')()),
            ('school_year', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['profiles.SchoolYear'])),
            ('teacher', self.gf('django.db.models.fields.related.ForeignKey')(related_name='students', to=orm['profiles.Teacher'])),
            ('family', self.gf('django.db.models.fields.related.ForeignKey')(related_name='children', to=orm['profiles.FamilyUser'])),
        ))
        db.send_create_signal(u'profiles', ['Child'])

        # Adding model 'Registration'
        db.create_table(u'profiles_registration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, db_index=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, db_index=True, blank=True)),
            ('course', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participants', to=orm['activities.Course'])),
            ('child', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['profiles.Child'])),
        ))
        db.send_create_signal(u'profiles', ['Registration'])

        # Adding unique constraint on 'Registration', fields ['course', 'child']
        db.create_unique(u'profiles_registration', ['course_id', 'child_id'])

        # Adding model 'SchoolYear'
        db.create_table(u'profiles_schoolyear', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('year', self.gf('django.db.models.fields.PositiveIntegerField')(unique=True)),
        ))
        db.send_create_signal(u'profiles', ['SchoolYear'])

        # Adding model 'Teacher'
        db.create_table(u'profiles_teacher', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=50, db_index=True)),
        ))
        db.send_create_signal(u'profiles', ['Teacher'])

        # Adding M2M table for field years on 'Teacher'
        db.create_table(u'profiles_teacher_years', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('teacher', models.ForeignKey(orm[u'profiles.teacher'], null=False)),
            ('schoolyear', models.ForeignKey(orm[u'profiles.schoolyear'], null=False))
        ))
        db.create_unique(u'profiles_teacher_years', ['teacher_id', 'schoolyear_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'Registration', fields ['course', 'child']
        db.delete_unique(u'profiles_registration', ['course_id', 'child_id'])

        # Deleting model 'FamilyUser'
        db.delete_table(u'profiles_familyuser')

        # Removing M2M table for field groups on 'FamilyUser'
        db.delete_table('profiles_familyuser_groups')

        # Removing M2M table for field user_permissions on 'FamilyUser'
        db.delete_table('profiles_familyuser_user_permissions')

        # Deleting model 'Child'
        db.delete_table(u'profiles_child')

        # Deleting model 'Registration'
        db.delete_table(u'profiles_registration')

        # Deleting model 'SchoolYear'
        db.delete_table(u'profiles_schoolyear')

        # Deleting model 'Teacher'
        db.delete_table(u'profiles_teacher')

        # Removing M2M table for field years on 'Teacher'
        db.delete_table('profiles_teacher_years')


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
            'teacher': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'students'", 'to': u"orm['profiles.Teacher']"})
        },
        u'profiles.familyuser': {
            'Meta': {'object_name': 'FamilyUser'},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'country': ('django.db.models.fields.CharField', [], {'default': "u'Switzerland'", 'max_length': '100'}),
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '255', 'db_index': 'True'}),
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
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'zipcode': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'profiles.registration': {
            'Meta': {'unique_together': "(('course', 'child'),)", 'object_name': 'Registration'},
            'child': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['profiles.Child']"}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participants'", 'to': u"orm['activities.Course']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'})
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
            'years': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['profiles.SchoolYear']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['profiles']