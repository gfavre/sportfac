from django import template

from ..models import ChildActivityLevel, Registration


register = template.Library()


@register.filter
def child_level(child, course):
    level, created = ChildActivityLevel.objects.get_or_create(child=child, activity=course.activity)
    return level


@register.filter
def child_announced_level(child, course):
    """Montreux ski specific"""
    try:
        registration = Registration.objects.get(course=course, child=child)
    except Registration.DoesNotExist:
        return ''
    qs = registration.extra_infos.filter(key__question_label='Niveau de ski/snowboard',
                                         key__in=registration.course.extra.all())
    if qs.exists():
        return qs.last().value
    return ''

