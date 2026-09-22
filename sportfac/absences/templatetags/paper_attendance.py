from django import template
from django.conf import settings

from absences.paper import next_attendance_date


register = template.Library()


@register.inclusion_tag("absences/paper-attendance-button.html")
def paper_attendance_button(course):
    enabled = settings.KEPCHUP_PAPER_ATTENDANCE
    return {"enabled": enabled, "course": course, "day": next_attendance_date(course) if enabled else None}
