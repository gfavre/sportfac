import math

from django import template
from django.utils.safestring import mark_safe

import phonenumbers


register = template.Library()


@register.filter(is_safe=True)
def money_html(value):
    try:
        number = float(value)
        frac, integer = math.modf(number)
        if frac:
            return mark_safe(f'CHF <span class="value">{number:1,.2f}</span>'.replace(",", "'"))
        return mark_safe(f'CHF <span class="value">{number:1,.0f}.-</span>'.replace(",", "'"))
    except ValueError:
        return value
    except TypeError:
        return value


@register.filter(is_safe=True)
def money(value):
    try:
        number = float(value)
        frac, integer = math.modf(number)
        if frac:
            return mark_safe(f"CHF {number:1,.2f}".replace(",", "'").replace("CHF -", "<strong>-</strong> CHF "))
        return mark_safe(f"CHF {number:1,.0f}.-".replace(",", "'").replace("CHF -", "<strong>-</strong> CHF "))
    except ValueError:
        return "n/a"
    except TypeError:
        return "n/a"


@register.filter(is_safe=True)
def money_sign(value):
    try:
        number = float(value)
        frac, integer = math.modf(number)
        if frac:
            return mark_safe(
                f"CHF {number:+1,.2f}".replace(",", "'").replace("CHF -", "– CHF ").replace("CHF +", "+ CHF ")
            )
        return mark_safe(
            f"CHF {number:+1,.0f}.-".replace(",", "'").replace("CHF -", "– CHF ").replace("CHF +", "+ CHF ")
        )
    except ValueError:
        return value
    except TypeError:
        return value


@register.filter(is_safe=True)
def iban(value):
    if value is None:
        return value
    grouping = 4
    value = value.upper().replace(" ", "").replace("-", "")
    return " ".join(value[i : i + grouping] for i in range(0, len(value), grouping))


@register.filter(is_safe=True)
def phone(value, phone_format="national"):
    """phone numbers and formats it"""
    if value in (None, ""):
        return ""
    if isinstance(value, phonenumbers.PhoneNumber):
        if phone_format.lower() == "e164":
            return value.as_e164
        if phone_format.lower() == "international" or value.country_code != 41:
            return value.as_international
        if phone_format.lower() == "rfc3966":
            return value.as_rfc3966
        return value.as_national

    fm = phonenumbers.PhoneNumberFormat.NATIONAL
    if phone_format.lower() == "e164":
        fm = phonenumbers.PhoneNumberFormat.E164
    elif phone_format.lower() == "international":
        fm = phonenumbers.PhoneNumberFormat.INTERNATIONAL
    elif phone_format.lower() == "rfc3966":
        fm = phonenumbers.PhoneNumberFormat.RFC3966
    try:
        number = phonenumbers.parse(value, "CH")
        return phonenumbers.format_number(number, fm)
    except phonenumbers.NumberParseException:
        return value


@register.filter(is_safe=True)
def ahv(value):
    if value is None:
        return value
    value = value.replace(" ", "").replace(".", "")
    if value:
        return f"{value[0:3]}.{value[3:7]}.{value[7:11]}.{value[11:]}"
    return value
