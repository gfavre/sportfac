from django.utils import timezone

from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from constance.admin import config

from profiles.models import Registration
from activities.models import Activity

class Step:
    def __init__(self, request, id, title, urlname, activable):
        self.id = id
        self.title = title
        self.url = reverse(urlname)
        self.activable = activable
        self.current = request.path == self.url
    
        

def can_register(user):
    if not user.is_authenticated() or user.finished_registration:
        return False
    return user.children.count() > 0

def can_confirm(user):
    if not user.is_authenticated() or user.finished_registration:
        return False
    return Registration.objects.filter(child__in=user.children.all()).count() > 0

def can_pay(user):
    if not user.is_authenticated():
        return False
    return user.finished_registration


def wizard_context(request):
    about = Step(request, 'about-step', _("About you"), 'wizard_account', True)
    children = Step(request, 'children-step', _("Your children"), 'wizard_children', request.user.is_authenticated)
    activities = Step(request, 'activities-step', _("Register activities"), 'wizard_activities', 
                      can_register(request.user))
    confirmation = Step(request, 'confirm-step',_("Confirmation"), 'wizard_confirm', 
                        can_confirm(request.user))
    billing = Step(request, 'billing-step', _("Billing"), 'wizard_billing', can_pay(request.user))
    
    
    steps = [about, children, activities, confirmation, billing]
    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
    
    previous_step = next_step = None
    previous_steps = filter(lambda x: x.activable, steps[:current])
    if len(previous_steps):
        previous_step = previous_steps[-1]

    next_steps = filter(lambda x: x.activable, steps[current + 1:])
    if len(next_steps):
        next_step = next_steps[0]
    
    return {'previous_step': previous_step,
            'next_step': next_step,
            'steps': steps,
            'max_step': [step.url for step in steps if step.activable][-1]}

def registration_opened_context(request):
    start = config.START_REGISTRATION
    end = config.END_REGISTRATION
    return {'registration_opened': start <= timezone.now() <= end,
            'registration_start': start,
            'registration_end': end}


def activities_context(request):
    return {'activities': Activity.objects.all()}