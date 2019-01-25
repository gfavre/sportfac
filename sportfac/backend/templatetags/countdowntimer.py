# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.utils.timezone import now

register = template.Library()


@register.inclusion_tag('backend/countdown.html', takes_context=True)
def countdown(context, date):
    sekizai_context = getattr(settings, 'SEKIZAI_VARNAME', 'SEKIZAI_CONTENT_HOLDER')
    return {'countdown_date': date,
            'now': now(),
            'remaining_days': (date - now()).days,
            sekizai_context: context[sekizai_context]}
