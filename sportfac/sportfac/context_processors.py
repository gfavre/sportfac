from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse
 

class Step:
    def __init__(self, request, title, urlname, activable):
        self.title = title
        self.url = reverse(urlname)
        self.activable = activable
        self.current = request.path == self.url
    
        
    

def wizard_context(request):
    about = Step(request, _("About you"), 'profiles_account', True)
    children = Step(request, _("Your children"), 'profiles_children', request.user.is_authenticated)
    activities = Step(request, _("Register activities"), 'activities-list', 
                      request.user.is_authenticated() and request.user.children.count())
    confirmation = Step(request, _("Confirmation"), 'home', False)
    billing = Step(request, _("Billing"), 'home', False)
    
    
    steps = [about, children, activities, confirmation, billing]
    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
    return {'show_wizard': len(filter(lambda x: x.current, steps)),
            'previous': current != 0 and steps[current - 1] or None,
            'next': current != len(steps) -1 and steps[current + 1] or None,
            'steps': steps}