from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from activities.models import Activity
from backend.models import YearTenant
from registrations.models import Bill, Registration


class Step:
    def __init__(self, request, id, title, urlname, activable):
        self.id = id
        self.title = title
        self.url = reverse(urlname)
        self.activable = activable
        self.current = request.path == self.url
    


def is_authenticated(request):
    return request.user.is_authenticated()

def can_register(request):
    return True#not is_authenticated(request)

def can_register_activities(request):
    return is_authenticated(request) and request.user.children.count() > 0

def can_confirm(request):
    return can_register_activities(request) and \
           Registration.objects.waiting().filter(
                child__in=request.user.children.all()
           ).count() > 0

def can_pay(request):
    return can_register_activities(request) and Bill.objects.filter(status=Bill.STATUS.just_created, family=request.user).count() > 0




def wizard_context(request):
    about = Step(request, 'about-step', _("About you"), 'wizard_account', 
                 can_register(request))
    children = Step(request, 'children-step', _("Your children"), 'wizard_children', 
                    is_authenticated(request))
    activities = Step(request, 'activities-step', _("Register activities"), 'wizard_activities', 
                      can_register_activities(request))
    confirmation = Step(request, 'confirm-step',_("Confirmation"), 'wizard_confirm', 
                        can_confirm(request))
    billing = Step(request, 'billing-step', _("Billing"), 'wizard_billing', 
                   can_pay(request))
        
    if settings.KEPCHUP_NO_PAYMENT:
        steps = [about, children, activities, confirmation]
    else:
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
            'registration_phase': request.PHASE,
            'registration_start': start,
            'registration_end': end,
            'registration_past': start <= end <= now,
            'registration_due': now <= start <= end,
            'minutes_spent': minutes_spent,
            'minutes_total': minutes_total,}


def activities_context(request):
    return {'activities': Activity.objects.visible()}

def tenants_context(request):
    if request.user.is_authenticated() and request.user.is_manager:
        return {'tenants': YearTenant.objects.all()}
    return {}

def kepchup_context(request):
    return {
        'USE_ABSENCES': settings.KEPCHUP_USE_ABSENCES,
        'IMPORT_CHILDREN': settings.KEPCHUP_IMPORT_CHILDREN,
        'PREFILL_YEARS_WITH_TEACHERS': settings.KEPCHUP_PREFILL_YEARS_WITH_TEACHERS,
        'NO_PAYMENT': settings.KEPCHUP_NO_PAYMENT,
        'NO_TERMS': settings.KEPCHUP_NO_TERMS,
        'NO_SSF': settings.KEPCHUP_NO_SSF,
        'CHILD_SCHOOL': settings.KEPCHUP_CHILD_SCHOOL,
        'EMERGENCY_NUMBER_MANDATORY': settings.KEPCHUP_EMERGENCY_NUMBER_MANDATORY,
        'DISPLAY_PARENT_CITY': settings.KEPCHUP_DISPLAY_PARENT_CITY,
        'CALENDAR_DISPLAY_DATES': settings.KEPCHUP_CALENDAR_DISPLAY_DATES,
        'CALENDAR_DISPLAY_COURSE_NAMES': settings.KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES,
        'BIB_NUMBERS': settings.KEPCHUP_BIB_NUMBERS,
        'FICHE_SALAIRE_MONTREUX': settings.KEPCHUP_FICHE_SALAIRE_MONTREUX,
        'REGISTRATION_LEVELS': settings.KEPCHUP_REGISTRATION_LEVELS,
    }