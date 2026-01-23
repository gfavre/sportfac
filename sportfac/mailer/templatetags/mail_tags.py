import os
import re

import six.moves.html_entities
from django import template


_EXTENSION_ICON_MAP = {
    "icon-file-pdf": {"pdf"},
    "icon-file-image": {"png", "jpg", "jpeg", "gif", "tif", "tiff"},
    "icon-file-code": {"htm", "html", "xhtml"},
    "icon-file-word": {"doc", "docx"},
    "icon-file-excel": {"xls", "xlsx"},
    "icon-file-powerpoint": {"ppt", "pptx"},
    "icon-file-archive": {"zip", "rar", "gz", "tar"},
    "icon-doc-text": {"txt"},
    "icon-file-audio": {"mp3", "aac"},
    "icon-file-video": {"mpg", "mp4", "mkv"},
}

register = template.Library()


@register.filter(is_safe=True)
def unescape(value):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(six.moves.html_entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub(r"&#?\w+;", fixup, value)


@register.filter
def filename(value):
    if value is None:
        return ""

        # Case 1: Django FileField / FieldFile
    if hasattr(value, "name"):
        return os.path.basename(value.name)

        # Case 2: Object with `.file.name`
    if hasattr(value, "file") and hasattr(value.file, "name"):
        return os.path.basename(value.file.name)

        # Case 3: plain string path
    if isinstance(value, str):
        return os.path.basename(value)

    return ""


@register.filter
def fileicon(value):
    name = filename(value)
    if not name:
        return "icon-doc"
    _, ext = os.path.splitext(name)
    extension: str = ext.lstrip(".").lower()

    for icon, extensions in _EXTENSION_ICON_MAP.items():
        if extension in extensions:
            return icon
    return "icon-doc"


@register.filter
def fileurl(value):
    return value.file.url
