import math

from django.utils.translation import ugettext as _
from django import template

import phonenumbers


register = template.Library()

@register.filter(is_safe=True)
def money(value):
    try:
        number = float(value)
        frac, integer = math.modf(number)
        if frac:
            return "CHF {:1,.2f}".format(number).replace(',', "'")
        else:
            return "CHF {:1,.0f}.-".format(number).replace(',', "'")
    except ValueError:
        return value
    except TypeError:
        return value

@register.filter(is_safe=True)
def iban(value):
    if value is None:
            return value
    grouping = 4
    value = value.upper().replace(' ', '').replace('-', '')
    return ' '.join(value[i:i + grouping] for i in range(0, len(value), grouping))   


@register.filter(is_safe=True)
def phone(value, format='national'):
    "phone numbers and formats it"
    if value in (None, ''):
        return ''

    if isinstance(value, phonenumbers.PhoneNumber):
        if format.lower() == 'e164':
            return value.as_e164
        elif format.lower() == 'international':
            return value.as_international
        elif format.lower() == 'rfc3966':
            return value.as_rfc3966
        return value.as_national

    fm = phonenumbers.PhoneNumberFormat.NATIONAL
    if format.lower() == 'e164':
        fm = phonenumbers.PhoneNumberFormat.E164
    elif format.lower() == 'international':
        fm = phonenumbers.PhoneNumberFormat.INTERNATIONAL
    elif format.lower() == 'rfc3966':
        fm = phonenumbers.PhoneNumberFormat.RFC3966
    try:
        number = phonenumbers.parse(value, 'CH')
        return phonenumbers.format_number(number, fm)
    except phonenumbers.NumberParseException:
        return value


@register.filter(is_safe=True)
def ahv(value):
    if value is None:
        return value
    value = value.replace(' ', '').replace('.', '')
    if value:
        return '%s.%s.%s.%s' % (value[0:3], value[3:7], value[7:11], value[11:])
    return value
