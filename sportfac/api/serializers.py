# -*- coding:utf-8 -*-
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from absences.models import Absence, Session
from activities.models import Activity, Course, ExtraNeed
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser, School, SchoolYear
from registrations.models import Child, ExtraInfo, Registration, ChildActivityLevel
from schools.models import Building, Teacher
from waiting_slots.models import WaitingSlot


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number')


class MultiCourseInlineSerializer(serializers.ModelSerializer):
    start_time_mon = serializers.TimeField(format='%H:%M')
    end_time_mon = serializers.TimeField(format='%H:%M')
    start_time_tue = serializers.TimeField(format='%H:%M')
    end_time_tue = serializers.TimeField(format='%H:%M')
    start_time_wed = serializers.TimeField(format='%H:%M')
    end_time_wed = serializers.TimeField(format='%H:%M')
    start_time_thu = serializers.TimeField(format='%H:%M')
    end_time_thu = serializers.TimeField(format='%H:%M')
    start_time_fri = serializers.TimeField(format='%H:%M')
    end_time_fri = serializers.TimeField(format='%H:%M')
    start_time_sat = serializers.TimeField(format='%H:%M')
    end_time_sat = serializers.TimeField(format='%H:%M')
    start_time_sun = serializers.TimeField(format='%H:%M')
    end_time_sun = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Course
        fields = (
            'start_time_mon', 'end_time_mon', 'start_time_tue', 'end_time_tue', 'start_time_wed', 'end_time_wed',
            'start_time_thu', 'end_time_thu', 'start_time_fri', 'end_time_fri', 'start_time_sat', 'end_time_sat',
            'start_time_sun', 'end_time_sun',
        )


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
    all_day = serializers.SerializerMethodField()
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')
    multi_course = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ('id', 'course_type', 'number', 'day', 'start_date', 'end_date', 'all_day', 'start_time', 'end_time',
                  'schoolyear_min', 'schoolyear_max', 'min_birth_date', 'max_birth_date', 'instructors', 'multi_course')

    @staticmethod
    def get_all_day(obj):
        return obj.is_camp

    @staticmethod
    def get_multi_course(obj):
        if not obj.is_multi_course:
            return None
        return MultiCourseInlineSerializer(obj).data


class CourseSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(many=False)
    instructors = InstructorSerializer(read_only=True, many=True)
    all_day = serializers.SerializerMethodField()
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')
    multi_course = serializers.SerializerMethodField()
    count_participants = serializers.IntegerField(source='nb_participants')

    class Meta:
        model = Course
        fields = ('id', 'course_type', 'number', 'name', 'instructors',
                  'activity', 'price', 'price_description',
                  'price_local', 'price_family', 'price_local_family',
                  'number_of_sessions', 'day', 'start_date', 'end_date', 'all_day', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 'count_participants',
                  'count_participants',
                  'schoolyear_min', 'schoolyear_max', 'multi_course', 'min_birth_date', 'max_birth_date',)
        read_only_fields = fields

    @staticmethod
    def get_all_day(obj):
        return obj.is_camp

    @staticmethod
    def get_multi_course(obj):
        if not obj.is_multi_course:
            return None
        return MultiCourseInlineSerializer(obj).data


class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ('id', 'name', 'number', 'courses')

    def get_courses(self, obj):
        courses = [course for course in obj.courses.order_by('start_date') if course.visible]
        return CourseInlineSerializer(courses, many=True, read_only=True).data


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ('id', 'name', 'address', 'zipcode', 'city', 'country')


class SchoolYearField(serializers.RelatedField):
    def to_representation(self, value):
        return value.year

    def to_internal_value(self, data):
        return SchoolYear.objects.get(year=data)


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
    avs = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Child
        fields = ('id', 'ext_id', 'status', 'first_name', 'last_name', 'sex',
                  'nationality', 'language', 'emergency_number',
                  'birth_date', 'school_year', 'teacher', 'school', 'other_school', 'avs')
        depth = 1
        read_only_fields = ('id', 'ext_id', 'status')

    # def validate_avs(self, value):
    #     if value is None or value == '':
    #         return None
    #     try:
    #         RegexValidator(regex=ssn_re)(value),  # enough numbers
    #         validators.EANValidator(strip_nondigits=True)(value)  # valid checksum
    #     except ValidationError:
    #         raise serializers.ValidationError(_("Invalid AVS number"))
    #     return value


class RegistrationSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(queryset=Child.objects.all())
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.visible().select_related('activity'))

    class Meta:
        model = Registration
        fields = ('id', 'child', 'course', 'status')

    def validate(self, data):
        if data['course'].full:
            raise serializers.ValidationError(_("Course is full"))

        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            if data['child'].school_year and data['child'].school_year.year not in data['course'].school_years:
                raise serializers.ValidationError(
                    _("This course is not opened to children of school year %(year)s") % {'year': data['child'].school_year}
                )
        else:
            if not (data['course'].max_birth_date <= data['child'].birth_date <= data['course'].min_birth_date ):
                raise serializers.ValidationError(
                    _("This course is not opened to children of this age")
                )
        if data["child"].registrations.count() >= global_preferences_registry.manager()['MAX_REGISTRATIONS']:
            raise serializers.ValidationError(
                _("Max number of registrations reached.")
            )
        return data


class WaitingSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaitingSlot
        fields = ('id', 'child', 'course')


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


class InlineChildrenSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    url = serializers.URLField(source='get_backend_detail_url', read_only=True)

    class Meta:
        model = Child
        fields = ('id', 'full_name', 'url')


class FamilySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    children = InlineChildrenSerializer(many=True)
    finished_registrations = serializers.BooleanField(source='profile.finished_registering')
    has_paid = serializers.BooleanField(source='profile.has_paid_all')
    last_registration = serializers.DateTimeField(source='profile.last_registration')
    last_registration_natural = serializers.SerializerMethodField()
    registered_this_period = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    class Meta:
        model = FamilyUser
        fields = ('id', 'full_name', 'first_name', 'last_name', 'email', 'zipcode', 'city', 'children',
                  'finished_registrations', 'has_paid', 'last_registration', 'last_registration_natural',
                  'registered_this_period',
                  'actions')

    @staticmethod
    def get_last_registration_natural(obj):
        return naturaltime(obj.last_registration)

    @staticmethod
    def get_registered_this_period(obj):
        return obj.last_registration is not None

    def get_actions(self, obj):
        return [
            {
                'url': obj.get_backend_url(),
                'label': _("User details"),
                'icon_class': 'icon-user'
            },
            {
                'url': obj.get_update_url(),
                'label': _("Update user"),
                'icon_class': 'icon-edit'
            },
            {
                'url': obj.get_delete_url(),
                'label': _("Delete user"),
                'icon_class': 'icon-trash'
            },
        ]


class InlineCourseSerializer(serializers.ModelSerializer):
    activity = serializers.StringRelatedField(read_only=True)
    url = serializers.URLField(source='get_backend_url', read_only=True)

    class Meta:
        model = Course
        fields = ('id', 'activity', 'number', 'url')


class InstructorSerializer(FamilySerializer):
    course = InlineCourseSerializer(many=True)

    class Meta:
        model = FamilyUser
        fields = ('id', 'full_name', 'first_name', 'last_name', 'course', 'actions')