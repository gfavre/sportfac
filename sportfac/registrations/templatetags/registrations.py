from django import template
from django.utils.safestring import mark_safe

from ..models import ExtraInfo


register = template.Library()


@register.simple_tag
def get_extra_info_td(registration, question):
    try:
        response = registration.extra_infos.get(key=question)
    except ExtraInfo.DoesNotExist:
        return mark_safe("<td></td>")
    formatted_response = response.value
    if question.type == "B":
        if response.value == "1":
            formatted_response = """<i class="icon-ok-circled text-success"></i>"""
        else:
            formatted_response = """<i class="icon-cancel-circled text-danger"></i>"""
    return mark_safe("""<td data-order="{}">{}</td>""".format(response.value, formatted_response))
