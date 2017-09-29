
from django import template
 
register = template.Library()

@register.filter(is_safe=True)
def index(aList, idx):
    return aList[int(idx)]


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)