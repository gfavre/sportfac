import math
from django import template

register = template.Library()

@register.filter(is_safe=True)
def swissfranc(value):
    try:
        number = float(value)
        frac, integer = math.modf(number)
        if frac:
            return "CHF {:1,.2f}".format(number).replace(',', "'")
        else:
            return "CHF {:1,.0f}.-".format(number).replace(',', "'")
    except ValueError:
        return value        