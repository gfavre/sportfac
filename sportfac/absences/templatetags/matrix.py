from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

from django import template


register = template.Library()


@register.filter(is_safe=True)
def index(a_list, idx):
    return a_list[int(idx)]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def add_pdf_param(url):
    params = {"pdf": 1}
    url_parts = list(urlparse(url))
    query = dict(parse_qsl(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query)
    return urlunparse(url_parts)
