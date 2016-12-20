from django import template

register = template.Library()

@register.filter(is_safe=True)
def answer_to(registration, question):
    if question.isdigit():
        qs = registration.extra_infos.filter(key__pk=int(question), key__in=registration.course.extra.all())
    else:
        qs = registration.extra_infos.filter(key__question_label=question, key__in=registration.course.extra.all())
    if qs.count():
        return qs.last().value
    return ''
