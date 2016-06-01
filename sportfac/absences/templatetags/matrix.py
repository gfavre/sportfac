
from django import template
 
register = template.Library()

@register.filter(is_safe=True)
def index(aList, idx):
    return aList[int(idx)]