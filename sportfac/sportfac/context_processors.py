# -*- coding: utf-8 -*-
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.timezone import now

from dynamic_preferences.registries import global_preferences_registry

from activities.models import Activity
from appointments.models import Appointment
from backend.models import YearTenant
from registrations.models import Bill, Registration


class Step:
    def __init__(self, request, identifier, title, urlname, activable):
        self.id = identifier
        self.title = title
        self.url = reverse(urlname)
        self.activable = activable
        self.current = request.path == self.url

    def __unicode__(self):
        return self.id

    def __str__(self):
        return self.id


def is_authenticated(request):
    return request.user.is_authenticated()


def can_register(request):
    return True  # not is_authenticated(request)


def can_register_activities(request):
    return is_authenticated(request) and request.user.children.exists()


def can_pay(request):
    return Bill.objects.filter(status=Bill.STATUS.just_created, family=request.user).exists()


def wizard_context(request):
    authenticated = is_authenticated(request)
    can_register_activities = False
    can_confirm = False
    can_pay = False
    can_make_appointment = False
    if authenticated:
        children_qs = request.user.children.all()
        can_register_activities = children_qs.exists()
        can_confirm = can_register_activities and Registration.waiting.filter(child__in=children_qs).exists()
        can_pay = can_register_activities and Bill.objects.filter(status=Bill.STATUS.just_created,
                                                                  family=request.user).exists()
        can_make_appointment = can_pay and request.user.montreux_needs_appointment


    about = Step(
        request, 'about-step', settings.KEPCHUP_ALTERNATIVE_ABOUT_LABEL or _("About you"),
        'wizard_account', can_register(request)
    )
    children = Step(
        request, 'children-step', settings.KEPCHUP_ALTERNATIVE_CHILDREN_LABEL or _("Your children"),
        'wizard_children', is_authenticated(request))
    activities = Step(
        request, 'activities-step', settings.KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL or _("Register activities"),
        'wizard_activities', can_register_activities
    )
    confirmation = Step(
        request, 'confirm-step', settings.KEPCHUP_ALTERNATIVE_CONFIRM_LABEL or _("Confirmation"),
        'wizard_confirm',
        can_confirm
    )
    steps = [about, children, activities, confirmation]

    if settings.KEPCHUP_USE_APPOINTMENTS:
        appointment_step = Step(request, 'appointment-step', _("Appointments"), 'wizard_appointments',
                                can_make_appointment)
        steps += [appointment_step]
        if not settings.KEPCHUP_NO_PAYMENT:

            can_pay = can_pay and (not request.user.montreux_needs_appointment or
                                   Appointment.objects.filter(child__in=request.user.children.all()).exists())
            billing = Step(
                request, 'billing-step', settings.KEPCHUP_ALTERNATIVE_BILLING_LABEL or _("Billing"),
                'wizard_billing', can_pay
            )
            steps += [billing]
    else:
        if not settings.KEPCHUP_NO_PAYMENT:
            billing = Step(
                request, 'billing-step', settings.KEPCHUP_ALTERNATIVE_BILLING_LABEL or _("Billing"),
                'wizard_billing', can_pay)
            steps += [billing]

    current = 0
    for idx, step in enumerate(steps):
        if step.current:
            current = idx
            break
    previous_step = next_step = None
    if current != 0:
        previous_step = steps[current - 1]

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
    return {
        'registration_opened': request.REGISTRATION_OPENED,
        'registration_phase': request.PHASE,
        'registration_start': start,
        'registration_end': end,
        'registration_past': start <= end <= now,
        'registration_due': now <= start <= end,
        'minutes_spent': minutes_spent,
        'minutes_total': minutes_total
    }


def activities_context(request):
    return {'activities': Activity.objects.visible()}


def tenants_context(request):
    user = request.user
    if user.is_authenticated() and (user.is_manager or user.is_staff or user.is_superuser):
        return {'tenants': YearTenant.objects.all()}
    return {}


def kepchup_context(request):

    return {
        'FIRST_NAME_EDITABLE': 'first_name' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'LAST_NAME_EDITABLE': 'last_name' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'SEX_EDITABLE': 'sex' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'BIRTH_DATE_EDITABLE': 'birth_date' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'NATIONALITY_EDITABLE': 'nationality' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'LANGUAGE_EDITABLE': 'language' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'SCHOOL_YEAR_EDITABLE': 'school_year' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'BUILDING_EDITABLE': 'building' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'TEACHER_EDITABLE': 'teacher' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'ID_LAGAPEO_EDITABLE': 'id_lagapeo' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'EMERGENCY_NUMBER_EDITABLE': 'emergency_number' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'SCHOOL_EDITABLE': 'school' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'OTHER_SCHOOL_EDITABLE': 'other_school' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'BIB_NUMBER_EDITABLE': 'bib_number' not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        'USE_ABSENCES': settings.KEPCHUP_USE_ABSENCES,
        'ABSENCES_RELATE_TO_ACTIVITIES': settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES,
        'USE_BUILDINGS': settings.KEPCHUP_USE_BUILDINGS,
        'IMPORT_CHILDREN': settings.KEPCHUP_IMPORT_CHILDREN,
        'PREFILL_YEARS_WITH_TEACHERS': settings.KEPCHUP_PREFILL_YEARS_WITH_TEACHERS,
        'NO_PAYMENT': settings.KEPCHUP_NO_PAYMENT,
        'DISPLAY_FREE_WHEN_PRICE_IS_0': settings.KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0,
        'NO_TERMS': settings.KEPCHUP_NO_TERMS,
        'NO_SSF': settings.KEPCHUP_NO_SSF,
        'CHILD_SCHOOL': settings.KEPCHUP_CHILD_SCHOOL,
        'CHILD_SCHOOL_DISPLAY_OTHER': settings.KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER,
        'EMERGENCY_NUMBER_MANDATORY': settings.KEPCHUP_EMERGENCY_NUMBER_MANDATORY,
        'DISPLAY_PARENT_CITY': settings.KEPCHUP_DISPLAY_PARENT_CITY,
        'CALENDAR_DISPLAY_DATES': settings.KEPCHUP_CALENDAR_DISPLAY_DATES,
        'CALENDAR_DISPLAY_COURSE_NAMES': settings.KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES,
        'CALENDAR_HIDDEN_DAYS': settings.KEPCHUP_CALENDAR_HIDDEN_DAYS,
        'ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE': settings.KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE,
        'BIB_NUMBERS': settings.KEPCHUP_BIB_NUMBERS,
        'FICHE_SALAIRE_MONTREUX': settings.KEPCHUP_FICHE_SALAIRE_MONTREUX,
        'REGISTRATION_LEVELS': settings.KEPCHUP_REGISTRATION_LEVELS,
        'DISPLAY_CAR_NUMBER': settings.KEPCHUP_DISPLAY_CAR_NUMBER,
        'DISPLAY_REGISTRATION_NOTE': settings.KEPCHUP_DISPLAY_REGISTRATION_NOTE,
        'DISPLAY_NUMBER_OF_SESSIONS': settings.KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS,
        'PROTOCOL': settings.DEBUG and 'http://' or 'https://',
        'REGISTER_ACCOUNTS_AT_ANY_TIME': settings.KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME,
        'EXPLICIT_SESSION_DATES': settings.KEPCHUP_EXPLICIT_SESSION_DATES,
        'NO_EXTRAS': settings.KEPCHUP_NO_EXTRAS,
        'USE_SSO': settings.KEPCHUP_USE_SSO,
        'USE_APPOINTMENTS': settings.KEPCHUP_USE_APPOINTMENTS,
        'DISPLAY_LAGAPEO': settings.KEPCHUP_DISPLAY_LAGAPEO,
        'DISPLAY_OVERLAP_HELP': settings.KEPCHUP_DISPLAY_OVERLAP_HELP,
        'CAN_DELETE_CHILD': settings.KEPCHUP_CAN_DELETE_CHILD,
    }


def dynamic_preferences_context(request):
    global_preferences = global_preferences_registry.manager()
    return {
        'preferences_period_name': global_preferences['PERIOD_NAME'],
        'preference_other_instance_start_registration': global_preferences['phase__OTHER_START_REGISTRATION'],
        'other_instance_started_registrations': global_preferences['phase__OTHER_START_REGISTRATION'] < now()
    }
