from django import template

from ..models import Registration


register = template.Library()


@register.simple_tag
def get_extra_info_td(registration, question):
    try:
        response = registration.extra_infos.get(key=question)
    except Registration.DoesNotExist:
        return "<td></td>"
    formatted_response = response.value
    if question.type == 'B':
        if response.value == '1':
            formatted_response = """<i class="icon-ok-circled text-success"></i>"""
        else:
            formatted_response = """<i class="icon-cancel-circled text-danger"></i>"""
    return """<td data-order="{}">{}</td>""".format(response.value, formatted_response)
