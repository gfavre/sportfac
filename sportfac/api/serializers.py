from rest_framework import serializers

from activities.models import Activity, Course, ExtraNeed
from profiles.models import FamilyUser, Child, Teacher, SchoolYear, Registration, ExtraInfo


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number')


class ResponsibleSerializer(serializers.ModelSerializer):
    first = serializers.CharField(source='first_name')
    last  = serializers.CharField(source='last_name')
    phone = serializers.CharField(source='best_phone')
    
    class Meta:
        model = FamilyUser
        fields = ('id', 'first', 'last', 'phone', 'email')
        read_only_fields = ('email',)


class CourseInlineSerializer(serializers.ModelSerializer):
    responsible = ResponsibleSerializer(read_only=True)
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')

    class Meta:
        model = Course
        fields = ('id', 'number', 'day', 'start_date', 'end_date', 'start_time', 'end_time', 
                  'schoolyear_min', 'schoolyear_max', 'responsible')


class CourseSerializer(serializers.ModelSerializer):
    activity = ActivitySerializer(many=False)
    responsible = ResponsibleSerializer(many=False)
    count_participants = serializers.IntegerField()
    start_time = serializers.TimeField(format='%H:%M')
    end_time = serializers.TimeField(format='%H:%M')
    
    class Meta:
        model = Course
        fields = ('id', 'number', 'responsible', 'activity', 'price', 'number_of_sessions', 'day', 
                  'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 'count_participants',
                  'schoolyear_min', 'schoolyear_max')


class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = CourseInlineSerializer(many=True)
    
    class Meta:
        model = Activity
        fields = ('id', 'name', 'number', 'courses')


class SchoolYearField(serializers.RelatedField):
    def to_representation(self, value):
        return value.year
    
    def to_internal_value(self, data):
        return SchoolYear.objects.get(year=data)


class TeacherSerializer(serializers.ModelSerializer):
    years = SchoolYearField(many=True, required=False, read_only=True)
    
    class Meta:
        model = Teacher
        fields = ('id', 'first_name', 'last_name', 'years' )


class SimpleChildrenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name')


class ChildrenSerializer(serializers.ModelSerializer):
    birth_date = serializers.DateField(format='iso-8601', input_formats=('iso-8601', '%d/%m/%Y', '%d.%m.%Y'))
    teacher = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                                 queryset=Teacher.objects.all())
    school_year = SchoolYearField(many=False, read_only=False, queryset=SchoolYear.objects.all())
    
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name', 'sex', 
                  'nationality', 'language',
                  'birth_date', 'school_year', 'teacher',)
        depth = 1


class RegistrationSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(read_only=True)
    course = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Registration
        fields = ('id', 'child', 'course',)


class ExtraSerializer(serializers.ModelSerializer):
    registration = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                                      queryset=Registration.objects.all())
    key = serializers.PrimaryKeyRelatedField(many=False, read_only=False,
                                             queryset=ExtraNeed.objects.all())
    
    class Meta:
        model = ExtraInfo
        fields = ('id', 'registration', 'key', 'info')