"""Template tag to display duration: 
{{ timedelta|duration }}

rendered as:
45mn

{{timedelta|seconds }}
rendered as: 2700

"""
from django import template
from django.utils.translation import ugettext as _
 
register = template.Library()

@register.filter(is_safe=True)
def duration(value, arg=False):
    "takes a time delta and renders it as duration"
    if value in (None, ''):
        return ''
    out = []
    try:
        if value.days > 1:
            out.append(_('%i days') % value.days)
        elif value.days == 1:
            out.append(_('1 day'))
        hours = value.seconds // 3600
        if hours > 1:
            out.append(_('%i hours') % hours)
        elif hours == 1:
            out.append(_('1 hour'))
        minutes = (value.seconds // 60) % 60
        if minutes > 1:
            out.append(_('%i minutes') % minutes)
        elif minutes == 1:
            out.append(_('1 minute'))
                
        if arg:
            seconds = value.seconds % 60
            if seconds > 1:
                out.append(_('%i seconds') % (value.seconds % 60))
            elif seconds == 1:
                out.append(_('1 second'))

        if not len(out):
            if arg:
                return _('0 second') 
            else:
                return _('0 minute')
        return ', '.join(out)
        
    except AttributeError:
        return ''


@register.filter(is_safe=True)
def seconds(value):
    "takes a time delta and renders it as number of seconds"
    if value in (None, ''):
        return 0
    out = []
    try:
        out = 0
        if value.days:
            out += 86400 * value.days# seconds in a day
        return out + value.seconds        
    except AttributeError:
        return 0

@register.filter(is_safe=True)
def hours(value):
    if value in (None, ''):
        return 0.0
    try:
        out = 0.0
        out += value.seconds / 3600.0
        if value.days:
            out += 24.0 * value.days
        return out
    except AttributeError:
        return 0.0
