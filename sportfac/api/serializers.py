from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.compat import smart_text

from activities.models import Activity, Course
from profiles.models import Child, Teacher, SchoolYear


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'image')

class CourseInlineSerializer(serializers.ModelSerializer):
    responsible = serializers.RelatedField(many=False)

    class Meta:
        model = Course
        fields = ('id', 'responsible', 'price', 'number_of_sessions', 'day', 
                  'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 
                  'schoolyear_min', 'schoolyear_max')



class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = CourseInlineSerializer(many=False)
    
    class Meta:
        model = Activity
        fields = ('id', 'name', 'image', 'courses')




class CourseSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(many=False)
    responsible = serializers.RelatedField(many=False)
    class Meta:
        model = Course
        fields = ('id', 'responsible', 'activity', 'price', 'number_of_sessions', 'day', 
                  'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 
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


class TeacherField(serializers.RelatedField):
    default_error_messages = {
        'does_not_exist': _("Object with %s does not exist."),
        'no_id': _('Teacher has no id.'),
    }
    
    def from_native(self, value):
        try:
            return self.queryset.get(id=value.get('id', -1))
        except ObjectDoesNotExist:
            msg = self.error_messages['does_not_exist'] % smart_text(value)
            raise ValidationError(msg)
        except IndexError:
            msg = self.error_messages['no_id']
            raise ValidationError(msg)
    
    def to_native(self, value):
        return (value.id, value.first_name, value.last_name, [sy.year for sy in value.years.all()])
    

class ChildrenSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='%d/%m/%Y', input_formats=('%d/%m/%Y',))
    teacher = TeacherField(many=False, read_only=False)
    school_year = SchoolYearField(many=False, read_only=False)
    
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name', 'sex', 
                  'birth_date', 'school_year', 'teacher',)
        depth = 1