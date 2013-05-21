from rest_framework import serializers

from activities.models import Activity, Course
from profiles.models import Child


class CourseSerializer(serializers.ModelSerializer):
    responsible = serializers.RelatedField(many=False)

    class Meta:
        model = Course
        fields = ('id', 'responsible', 'price', 'number_of_sessions', 'day', 
                  'start_date', 'end_date', 'start_time', 'end_time', 'place',
                  'min_participants', 'max_participants', 
                  'schoolyear_min', 'schoolyear_max')


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'name', 'image')

class ActivityDetailedSerializer(serializers.ModelSerializer):
    courses = CourseSerializer(many=False)
    
    class Meta:
        model = Activity
        fields = ('id', 'name', 'image', 'courses')



class ChildrenSerializer(serializers.ModelSerializer):
    teacher = serializers.RelatedField(many=False)
    class Meta:
        model = Child
        fields = ('id', 'first_name', 'last_name', 'school_year', 'teacher')