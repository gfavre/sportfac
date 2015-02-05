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
    
def has_finished(request):
    return request.user.finished_registration      

def can_register_activities(request):
    if not request.user.is_authenticated() or has_finished(request):
        return False
    return request.user.children.count() > 0

def can_confirm(request):
    if not request.user.is_authenticated() or has_finished(request):
        return False
    return Registration.objects.filter(child__in=request.user.children.all()).count() > 0

def can_pay(request):
    if not request.user.is_authenticated():
        return False
    return has_finished(request)

def can_register(request):
    if not request.user:
        return True
    return not has_finished(request)


def wizard_context(request):
    about = Step(request, 'about-step', _("About you"), 'wizard_account', can_register(request))
    children = Step(request, 'children-step', _("Your children"), 'wizard_children', not has_finished(request))
    activities = Step(request, 'activities-step', _("Register activities"), 'wizard_activities', 
                      can_register_activities(request))
    confirmation = Step(request, 'confirm-step',_("Confirmation"), 'wizard_confirm', 
                        can_confirm(request))
    billing = Step(request, 'billing-step', _("Billing"), 'wizard_billing', can_pay(request))
    
    
    steps = [about, children, activities, confirmation, billing]
    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
            break
    
    previous_step = next_step = None
    if current != 0:
        previous_step = steps[current -1]
    
    if current != len(steps) - 1:
        next_step = steps[current + 1]
    
    return {'previous_step': previous_step,
            'next_step': next_step,
            'steps': steps,
            'current_step': steps[current],
            'max_step': [step.url for step in steps if step.activable][-1]}


def registration_opened_context(request):
    start = request.REGISTRATION_START
    end = request.REGISTRATION_END
    now = timezone.now()
    minutes_spent = int((now - start).total_seconds() / 60)
    minutes_total = int((end - start).total_seconds() / 60)
    return {'registration_opened': request.REGISTRATION_OPENED,
            'registration_start': start,
            'registration_end': end,
            'registration_past': start <= end <= now,
            'registration_due': now <= start <= end,
            'minutes_spent': minutes_spent,
            'minutes_total': minutes_total,}


def activities_context(request):
    return {'activities': Activity.objects.all()}