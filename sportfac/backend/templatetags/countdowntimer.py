from django import template
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import gettext as _


register = template.Library()


@register.inclusion_tag("backend/countdown.html", takes_context=True)
def countdown(context, date):
    sekizai_context = getattr(settings, "SEKIZAI_VARNAME", "SEKIZAI_CONTENT_HOLDER")
    return {
        "countdown_date": date,
        "now": now(),
        "remaining_days": (date - now()).days,
        sekizai_context: context[sekizai_context],
    }


@register.filter
def human_readable_time(minutes):
    if minutes >= 1440:
        hours = minutes // 60
        return _("{hours} hours").format(hours=hours)
    return _("{minutes} minutes").format(minutes=minutes)
