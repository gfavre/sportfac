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
    
        


def wizard_context(request):
    about = Step(request, 'about-step', _("About you"), 'profiles_account', True)
    children = Step(request, 'children-step', _("Your children"), 'profiles_children', request.user.is_authenticated)
    activities = Step(request, 'activities-step', _("Register activities"), 'activities-list', 
                      request.user.is_authenticated() and request.user.children.count())
    confirmation = Step(request, 'confirm-step',_("Confirmation"), 'activities-confirm', True)#request.user.is_authenticated and Registration.objects.filter(child__in=request.user.children.all()).count() > 0)
    billing = Step(request, 'billing-step', _("Billing"), 'home', True)#request.user.is_authenticated and Registration.objects.filter(child__in=request.user.children.all()).count() > 0)
    
    
    steps = [about, children, activities, confirmation, billing]
    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
    return {'show_wizard': len(filter(lambda x: x.current, steps)),
            'previous_step': current != 0 and steps[current - 1] or None,
            'next_step': current != len(steps) -1 and steps[current + 1] or None,
            'steps': steps}