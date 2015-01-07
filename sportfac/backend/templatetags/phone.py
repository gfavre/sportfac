"""Template tag to display duration: 
{{ timedelta|duration }}

rendered as:
45mn

{{timedelta|seconds }}
rendered as: 2700

"""
from django import template
from django.utils.translation import ugettext as _

import phonenumbers
 
register = template.Library()

@register.filter(is_safe=True)
def swissphone(value, format='national'):
    "phone numbers and formats it"
    if value in (None, ''):
        return ''
    try:
        number = phonenumbers.parse(value, 'CH')
        fm = phonenumbers.PhoneNumberFormat.NATIONAL 
        if format.lower() == 'e164':
            fm = phonenumbers.PhoneNumberFormat.E164 
        elif format.lower() == 'international':
            fm = phonenumbers.PhoneNumberFormat.INTERNATIONAL 
        elif format.lower() == 'rfc3966':
            fm = phonenumbers.PhoneNumberFormat.RFC3966 
        return phonenumbers.format_number(number, fm)
        
    except phonenumbers.NumberParseException:
        return value