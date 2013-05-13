from rest_framework import serializers

from activities.models import Activity, Course


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
