
from django import template
from django.utils.translation import ugettext as _


register = template.Library()

@register.filter(is_safe=True)
def absence_status(status):
    vals = {'absent': _("Absent"),
            'excused': _("Excused"),
            'medical': _("Medical certificate"),
            'late': _("Late arrival"),
            'present': _("Present")}
    return vals.get(status)