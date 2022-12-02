from __future__ import absolute_import
from django import template


register = template.Library()


@register.filter(is_safe=True)
def answer_to(registration, question):
    if question.isdigit():
        qs = registration.extra_infos.filter(key__pk=int(question))
    else:
        qs = registration.extra_infos.filter(key__question_label__startswith=question)
    if qs.count():
        return qs.last().value
    return ''


@register.filter(is_safe=True)
def has_question(registration, question):
    if question.isdigit():
        qs = registration.course.extra.filter(pk=int(question))
    else:
        qs = registration.course.extra.filter(question_label=question)
    return qs.count() > 0
