import math
from django import template

register = template.Library()

@register.filter(is_safe=True)
def swissfranc(value):
    try:
        number = float(value)
        frac, integer = math.modf(value)
        if frac:
            return "CHF {:1.2f}".format(value)
        else:
            return "CHF {:1.0f}.-".format(value)
    except ValueError:
        return value        