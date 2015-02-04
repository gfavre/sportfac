from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.compat import smart_text

from activities.models import Activity, Course, Responsible
from profiles.models import Child, Teacher, SchoolYear, Registration, ExtraInfo


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number')

class ResponsibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Responsible
        fields = ('last', 'first', 'phone', 'email')



class CourseInlineSerializer(serializers.ModelSerializer):
    responsible = serializers.RelatedField(many=False)
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')


    class Meta:
        model = Course
        fields = ('id', 'number', 'day', 'start_date', 'end_date', 'start_time', 'end_time', 
                  'schoolyear_min', 'schoolyear_max')



class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = CourseInlineSerializer(many=False)
    
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number', 'courses')




class CourseSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(many=False)
    responsible = ResponsibleSerializer(many=False)
    count_participants = serializers.Field(source='count_participants')
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')
    
    class Meta:
        model = Course
        fields = ('id', 'number', 'responsible', 'activity', 'price', 'number_of_sessions', 'day', 
                  'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 'count_participants',
                  'schoolyear_min', 'schoolyear_max')


class SchoolYearField(serializers.RelatedField):
    def to_native(self, value):
        return value.year
    
    def from_native(self, value):
        return SchoolYear.objects.get(year=value)

class TeacherSerializer(serializers.ModelSerializer):
    years = SchoolYearField(many=True, required=False)
    
    class Meta:
        model = Teacher
        fields = ('id', 'first_name', 'last_name', 'years' )

class SimpleChildrenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name')


class ChildrenSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='iso-8601', input_formats=('iso-8601', '%d/%m/%Y', '%d.%m.%Y'))
    teacher = serializers.PrimaryKeyRelatedField(many=False, read_only=False)
    school_year = SchoolYearField(many=False, read_only=False)
    
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name', 'sex', 
                  'birth_date', 'school_year', 'teacher',)
        depth = 1

class RegistrationSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField()
    course = serializers.PrimaryKeyRelatedField()
    
    class Meta:
        model = Registration

class ExtraSerializer(serializers.ModelSerializer):
    registration = serializers.PrimaryKeyRelatedField(many=False, read_only=False)
    key = serializers.PrimaryKeyRelatedField(many=False, read_only=False)
    
    class Meta:
        model = ExtraInfo