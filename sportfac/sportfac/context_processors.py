from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from profiles.models import Registration

class Step:
    def __init__(self, request, id, title, urlname, activable):
        self.id = id
        self.title = title
        self.url = reverse(urlname)
        self.activable = activable
        self.current = request.path == self.url
    
        
def can_pay(user):
    if not user.is_authenticated():
        return False
    return Registration.objects.filter(child__in=user.children.all(), validated=True, paid=False).count() > 0

def can_confirm(user):
    if not user.is_authenticated():
        return False
    return Registration.objects.filter(child__in=user.children.all()).count() > 0

def can_register(user):
    if not user.is_authenticated():
        return False
    return user.children.count() > 0



def wizard_context(request):
    about = Step(request, 'about-step', _("About you"), 'profiles_account', True)
    children = Step(request, 'children-step', _("Your children"), 'profiles_children', request.user.is_authenticated)
    activities = Step(request, 'activities-step', _("Register activities"), 'activities-list', 
                      can_register(request.user))
    confirmation = Step(request, 'confirm-step',_("Confirmation"), 'activities-confirm', 
                        can_confirm(request.user))
    billing = Step(request, 'billing-step', _("Billing"), 'home', can_pay(request.user))
    
    
    steps = [about, children, activities, confirmation, billing]
    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
    return {'show_wizard': len(filter(lambda x: x.current, steps)),
            'previous_step': current != 0 and steps[current - 1] or None,
            'next_step': current != len(steps) -1 and steps[current + 1] or None,
            'steps': steps,
            'max_step': [step.url for step in steps if step.activable][-1]}