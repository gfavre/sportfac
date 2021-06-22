import htmlentitydefs
import os
import re

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
def fileicon(value):
    extension = value.file.name.split('.')[-1].lower()
    if extension == 'pdf':
        return 'icon-file-pdf'
    elif extension in ('png', 'jpg', 'gif', 'tif', 'tiff'):
        return 'icon-file-image'
    elif extension in ('htm', 'html', 'xhtml'):
        return 'icon-file-code'
    elif extension in ('doc', 'docx'):
        return 'icon-file-word'
    elif extension in ('xls', 'xlsx'):
        return 'icon-file-excel'
    elif extension in ('ppt', 'pptx'):
        return 'icon-file-powerpoint'
    elif extension in ('zip', 'rar', 'gz', 'tar'):
        return 'icon-file-archive'
    elif extension in ('txt',):
        return 'icon-doc-text'
    elif extension in ('mp3', 'aac'):
        return 'icon-file-audio'
    elif extension in ('mpg', 'mp4', 'mkv'):
        return 'icon-file-audio'
    return 'icon-doc-1'


@register.filter
def fileurl(value):
    return value.file.url