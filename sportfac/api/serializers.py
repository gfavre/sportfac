from rest_framework import serializers

from activities.models import Activity, Course
from profiles.models import Child


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



class ChildrenSerializer(serializers.ModelSerializer):
    teacher = serializers.RelatedField(many=False)
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name', 'school_year', 'teacher')