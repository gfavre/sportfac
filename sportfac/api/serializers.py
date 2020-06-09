# -*- coding:utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from absences.models import Absence, Session
from activities.models import Activity, Course, ExtraNeed
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser, School, SchoolYear
from registrations.models import Child, ExtraInfo, Registration, ChildActivityLevel
from schools.models import Building, Teacher


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number')


class InstructorSerializer(serializers.ModelSerializer):
    first = serializers.CharField(source='first_name')
    last = serializers.CharField(source='last_name')
    phone = serializers.CharField(source='best_phone')
    initials = serializers.CharField(source='get_initials', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = FamilyUser
        fields = ('id', 'first', 'last', 'phone', 'email', 'initials', 'full_name')
        read_only_fields = ('email', 'initials')


class CourseInlineSerializer(serializers.ModelSerializer):
    instructors = InstructorSerializer(read_only=True, many=True)
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Course
        fields = ('id', 'number', 'day', 'start_date', 'end_date', 'start_time', 'end_time',
                  'schoolyear_min', 'schoolyear_max', 'instructors')


class CourseSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(many=False)
    instructors = InstructorSerializer(read_only=True, many=True)
    count_participants = serializers.IntegerField()
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Course
        fields = ('id', 'number', 'name', 'instructors', 'activity', 'price', 'price_description',
                  'number_of_sessions', 'day', 'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 'count_participants',
                  'schoolyear_min', 'schoolyear_max')


class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ('id', 'name', 'number', 'courses')

    def get_courses(self, obj):
        courses = [course for course in obj.courses.all() if course.visible]
        return CourseInlineSerializer(courses, many=True, read_only=True).data


class SchoolYearField(serializers.RelatedField):
    def to_representation(self, value):
        return value.year

    def to_internal_value(self, data):
        return SchoolYear.objects.get(year=data)


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ('id', 'name', 'address', 'zipcode', 'city', 'country')


class TeacherSerializer(serializers.ModelSerializer):
    years = SchoolYearField(many=True, required=False, read_only=True)
    buildings = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Teacher
        fields = ('id', 'first_name', 'last_name', 'years', 'buildings')


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ('year',)


class SimpleChildrenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name')


class ChildrenSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='iso-8601', input_formats=('iso-8601', '%d/%m/%Y', '%d.%m.%Y'))
    teacher = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                                 queryset=Teacher.objects.all(), required=False, allow_null=True)
    school = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                                queryset=School.objects.filter(selectable=True),
                                                required=False, allow_null=True)
    school_year = SchoolYearField(many=False, read_only=False, queryset=SchoolYear.visible_objects.all())
    ext_id = serializers.IntegerField(source='id_lagapeo', required=False, allow_null=True, max_value=100000000)

    class Meta:
        model = Child
        fields = ('id', 'ext_id', 'status', 'first_name', 'last_name', 'sex',
                  'nationality', 'language', 'emergency_number',
                  'birth_date', 'school_year', 'teacher', 'school', 'other_school')
        depth = 1
        read_only_fields = ('id', 'ext_id', 'status')


class RegistrationSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.visible().select_related('activity'))

    class Meta:
        model = Registration
        fields = ('id', 'child', 'course', 'status')

    def validate(self, data):
        if data['course'].full:
            raise serializers.ValidationError(_("Course is full"))

        if data['child'].school_year and \
           data['child'].school_year.year not in data['course'].school_years:
            raise serializers.ValidationError(
                _("This course is not opened to children of school year %(year)s") % {'year': data['child'].school_year}
            )
        if data["child"].registrations.count() >= global_preferences_registry.manager()['MAX_REGISTRATIONS']:
            raise serializers.ValidationError(
                _("Max number of registrations reached.")
            )
        return data


class ExtraSerializer(serializers.ModelSerializer):
    registration = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                                      queryset=Registration.objects.all())
    key = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                             queryset=ExtraNeed.objects.all())

    class Meta:
        model = ExtraInfo
        fields = ('id', 'registration', 'key', 'value')


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildActivityLevel
        fields = ('id', 'before_level', 'after_level')


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildActivityLevel
        fields = ('id', 'note')


class ChildActivityLevelSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    activity = serializers.PrimaryKeyRelatedField(queryset=Activity.objects.all())

    class Meta:
        model = ChildActivityLevel
        fields = ('id', 'child', 'activity', 'before_level', 'after_level', 'note')


class SessionSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all().select_related('activity'))
    date = serializers.DateField()
    instructor = InstructorSerializer(allow_null=True)

    class Meta:
        model = Session
        fields = ('id', 'date', 'course', 'instructor')


class SessionUpdateSerializer(SessionSerializer):
    instructor = serializers.PrimaryKeyRelatedField(queryset=FamilyUser.instructors_objects.all(),
                                                    allow_null=True)


class AbsenceSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all())

    class Meta:
        model = Absence
        fields = ('id', 'status', 'child', 'session',)


class SetAbsenceSerializer(serializers.Serializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all())
    status = serializers.ChoiceField(choices=Absence.STATUS + ('present', _("Present")))


class ChangeCourseSerializer(serializers.Serializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    previous_course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    new_course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())


class CourseChangedSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='long_name')
    absence_url = serializers.CharField(source='get_backend_absences_url')

    class Meta:
        model = Course
        fields = ('id', 'name', 'absence_url')
