from django import template

register = template.Library()

@register.filter(is_safe=True)
def answer_to(registration, question):
    if question.isdigit():
        qs = registration.extra_infos.filter(key__pk=int(question))
    else:
        qs = registration.extra_infos.filter(key__question_label=question)
    if qs.count():
        return qs.last().value
    return ''
