from django import template
from django.utils.translation import gettext as _


register = template.Library()


@register.filter(is_safe=True)
def absence_status(status):
    vals = {
        "absent": _("Absent"),
        "excused": _("Excused"),
        "medical": _("Medical certificate"),
        "late": _("Late arrival"),
        "present": _("Present"),
        "canceled": _("Canceled course"),
    }
    return vals.get(status, _("n/a"))


@register.filter(is_safe=True)
def absence_to_status(absence, short=False):
    if short:
        return absence_short(absence.status)
    return absence_status(absence.status)


@register.filter(is_safe=True)
def absence_short(status):
    vals = {
        "absent": _("A"),
        "excused": _("E"),
        "medical": _("MC"),
        "late": _("LA"),
        "present": _("P"),
        "canceled": _("AA"),
    }
    return vals.get(status, _("n/a"))
