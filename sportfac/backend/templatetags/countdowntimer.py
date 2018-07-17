from datetime import datetime

from django import template
from django.conf import settings
from django.utils.timezone import now

register = template.Library()


@register.inclusion_tag('backend/countdown.html', takes_context=True)
def countdown(context, date):
    sezikai_ctx_var = getattr(settings, 'SEKIZAI_VARNAME', 'SEKIZAI_CONTENT_HOLDER')
    return {'countdown_date': date,
            'now': now(),
            sezikai_ctx_var: context[sezikai_ctx_var]}
