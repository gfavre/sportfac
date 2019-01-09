try:
    import urlparse
    from urllib import urlencode
except ImportError: # For Python 3
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
    params = {'pdf': 1}
    url_parts = list(urlparse.urlparse(url))
    query = dict(urlparse.parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlparse.urlunparse(url_parts)