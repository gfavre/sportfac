from django import template
from django.utils.translation import gettext as _

from ..models import Absence


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
def absence_class(absence):
    if absence.status == Absence.STATUS.present:
        return "success"
    if absence.status == Absence.STATUS.late:
        return "info"
    if absence.status in (Absence.STATUS.excused, Absence.STATUS.canceled):
        return "warning"
    return "danger"


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
