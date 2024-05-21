from django.conf import settings
from django.utils.translation import gettext_lazy as _

from import_export import fields, resources

from .models import Course


class CourseResource(resources.ModelResource):
    number = fields.Field(attribute="number", column_name=_("N°"))
    long_name = fields.Field(attribute="long_name", column_name=_("Course name"))
    limitations = fields.Field(column_name=_("Limitations"))
    day_name = fields.Field(column_name=_("Day"))
    schedule = fields.Field(column_name=_("Schedule"))
    place = fields.Field(column_name=_("Place"), attribute="place")
    instructors = fields.Field(column_name=_("Instructors"))
    instructors_phone = fields.Field(column_name=_("Instructors' phone"))
    instructors_email = fields.Field(column_name=_("Instructors' email"))
    participants = fields.Field(column_name=_("Participants number"))
    start_date = fields.Field(column_name=_("Start date"))
    end_date = fields.Field(column_name=_("End date"))

    class Meta:
        model = Course
        fields = (
            "number",
            "long_name",
            "limitations",
            "price",
            "day_name",
            "start_date",
            "end_date",
            "schedule",
            "place",
            "instructors",
            "instructors_phone",
            "instructors_email",
            "participants",
        )
        export_order = fields

    def dehydrate_price(self, course):
        if settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            return (
                f"{course.price}, {course.price_local} (local), {course.price_family}"
                f" (famille), {course.price_local_family} (local + famille)"
            )
        return course.price

    def dehydrate_instructors(self, course):
        return ", ".join(instructor.full_name for instructor in course.instructors.all())

    def dehydrate_instructors_phone(self, course):
        return ", ".join(str(instructor.best_phone.as_national) for instructor in course.instructors.all())

    def dehydrate_instructors_email(self, course):
        return ", ".join(instructor.email for instructor in course.instructors.all())

    def dehydrate_participants(self, course):
        return course.count_participants

    def dehydrate_schedule(self, course):
        start_time_formatted = course.start_time.strftime("%H:%M")
        end_time_formatted = course.end_time.strftime("%H:%M")
        return f"{start_time_formatted} - {end_time_formatted}"

    def dehydrate_day_name(self, course):
        return course.day_name

    def dehydrate_limitations(self, course):
        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            school_year_min = settings.KEPCHUP_YEAR_NAMES[course.schoolyear_min]
            school_year_max = settings.KEPCHUP_YEAR_NAMES[course.schoolyear_max]
            return f"{school_year_min} - {school_year_max}"
        return f"{course.age_min} - {course.age_max} ans"
