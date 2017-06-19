from import_export import resources, fields
from .models import Course

class CourseResource(resources.ModelResource):

    activity_name = fields.Field(attribute='activity__name', column_name='activity', readonly=True)
    name = fields.Field(attribute='name', column_name='displayed_name')
    instructors = fields.Field()
    participants = fields.Field()

    def dehydrate_instructors(self, course):
        return ', '.join(instructor.full_name for instructor in course.instructors.all())

    def dehydrate_participants(self, course):
        return course.count_participants

    class Meta:
        model = Course
        fields = ('number', 'activity_name', 'name', 'uptodate', 'visible', 'instructors', 'price',
                  'number_of_sessions', 'day', 'start_date', 'start_time', 'end_date', 'end_time',
                  'place', 'schoolyear_min', 'schoolyear_max', 'min_participants', 'max_participants',
                  'participants',)
        export_order = fields