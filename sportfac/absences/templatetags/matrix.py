from __future__ import absolute_import


try:
    import six.moves.urllib.parse
    from six.moves.urllib.parse import urlencode
except ImportError:  # For Python 3
    import urllib.parse as urlparse
    from urllib.parse import urlencode

from django import template


register = template.Library()


@register.filter(is_safe=True)
def index(aList, idx):
    return aList[int(idx)]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def add_pdf_param(url):
    params = {"pdf": 1}
    url_parts = list(six.moves.urllib.parse.urlparse(url))
    query = dict(six.moves.urllib.parse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return six.moves.urllib.parse.urlunparse(url_parts)
