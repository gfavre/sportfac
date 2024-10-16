from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sportfac.admin_utils import SportfacModelAdmin

from .models import Absence, Session


@admin.register(Session)
class SessionAdmin(SportfacModelAdmin):
    list_display = ("course_short", "date", "instructor_short")
    list_filter = ("date",)
    date_hierarchy = "date"
    search_fields = (
        "course__name",
        "course__activity__name",
        "course__number",
        "instructor__first_name",
        "instructor__last_name",
    )
    raw_id_fields = ("instructor", "course")

    def course_short(self, obj):
        return obj.course.short_name

    course_short.short_description = _("course")

    def instructor_short(self, obj):
        if obj.instructor:
            return obj.instructor.full_name
        return

    instructor_short.short_description = _("Instructor")

    def get_queryset(self, request):
        return (
            Session.objects.prefetch_related("absences")
            .select_related("course", "course__activity", "instructor")
            .order_by("-date")
        )


@admin.register(Absence)
class AbsenceAdmin(SportfacModelAdmin):
    date_hierarchy = "session__date"
    list_display = ("child", "get_date", "get_activity", "get_course", "status")
    list_filter = ("status",)
    raw_id_fields = ("child", "session")
    search_fields = (
        "child__first_name",
        "child__last_name",
        "session__course__number",
        "session__activity__name",
    )

    def get_queryset(self, request):
        return Absence.objects.select_related(
            "child", "session", "session__course", "session__activity"
        )

    def get_date(self, obj):
        return obj.session.date

    get_date.admin_order_field = "session__date"
    get_date.short_description = _("Date")

    def get_activity(self, obj):
        return obj.session.activity

    get_activity.admin_order_field = "session__activity"
    get_activity.short_description = _("Activity")

    def get_course(self, obj):
        return obj.session.course.short_name

    get_course.admin_order_field = "session__course"
    get_course.short_description = _("Course")
