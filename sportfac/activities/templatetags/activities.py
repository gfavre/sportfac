import re

from django import template
from django.utils.translation import gettext as _


register = template.Library()


@register.filter(name="course_number_display")
def course_number_display(course):
    # Check if the course number consists of digits
    if course.number and re.match(r"^\d", course.number):
        return _("Course #%(number)s") % {"number": course.number}
    return course.number
