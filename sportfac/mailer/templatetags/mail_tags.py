import os, re, htmlentitydefs
from django import template

register = template.Library()

@register.filter(is_safe=True)
def unescape(value):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, value)


@register.filter
def filename(value):
    return os.path.basename(value.file.name)
    
@register.filter
def fileurl(value):
    return os.path.basename(value.file.url)