from django.conf import settings
from django.db import connection
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.timezone import get_default_timezone, make_aware, now
from django.utils.translation import gettext as _

from activities.models import Activity
from backend.models import YearTenant
from dynamic_preferences.registries import global_preferences_registry


class Step:
    def __init__(self, request, identifier, title, urlname):
        self.id = identifier
        self.title = title
        self.url = reverse(urlname)
        self.current = request.path == self.url
        self.request = request
        self.activable = False

    def __str__(self):
        return self.id

    def ensure_activable(self):
        # Resolve returns a resolver_match that can be used to get view class and then call static method
        from sportfac.views import NotReachableException

        url = self.url
        if settings.FORCE_SCRIPT_NAME:
            # URL = /hiver/wizard => ça ne résout pas. à cause du /hiver
            url = url.replace(settings.FORCE_SCRIPT_NAME, "")
        try:
            resolve(url).func.view_class.check_initial_condition(self.request)
            self.activable = True
        except NotReachableException:
            self.activable = False
        return self.activable


def wizard_context(request):
    if "/wizard/" not in request.path:
        return {}
    # 1. list the possible steps given the configuration
    # 2. for each step, ensure it is reachable
    about = Step(
        request,
        "about-step",
        settings.KEPCHUP_ALTERNATIVE_ABOUT_LABEL or _("About you"),
        "wizard_account",
    )
    children = Step(
        request,
        "children-step",
        settings.KEPCHUP_ALTERNATIVE_CHILDREN_LABEL or _("Your children"),
        "wizard_children",
    )
    activities = Step(
        request,
        "activities-step",
        settings.KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL or _("Register activities"),
        "wizard_activities",
    )
    confirmation = Step(
        request,
        "confirm-step",
        settings.KEPCHUP_ALTERNATIVE_CONFIRM_LABEL or _("Confirmation"),
        "wizard_confirm",
    )
    all_steps = [about, children, activities, confirmation]
    if settings.KEPCHUP_USE_APPOINTMENTS:
        appointment_step = Step(
            request,
            "appointment-step",
            settings.KEPCHUP_ALTERNATIVE_APPOINTMENTS_LABEL or _("Appointments"),
            "wizard_appointments",
        )
        all_steps += [appointment_step]

    if not settings.KEPCHUP_NO_PAYMENT:
        billing_step = Step(
            request,
            "billing-step",
            settings.KEPCHUP_ALTERNATIVE_BILLING_LABEL or _("Billing"),
            "wizard_billing",
        )
        all_steps += [billing_step]

    for step in all_steps:
        step.ensure_activable()
        # if not step.ensure_activable():
        #    # If a step is not activable, there is no need to check activability of the next ones.
        #    # (activable is False unless ensured...)
        #    break

        #    # TODO ERREUR: le paiement est accessible ssi bill ouverte, même si confirmation

    current = 0
    for idx, step in enumerate(all_steps):
        if step.current:
            current = idx
            break
    previous_step = next_step = None
    if current != 0:
        previous_step = all_steps[current - 1]

    if current != len(all_steps) - 1:
        next_step = all_steps[current + 1]
    try:
        max_step = [step.url for step in all_steps if step.activable][-1]
    except IndexError:
        max_step = all_steps[current].url
    return {
        "previous_step": previous_step,
        "next_step": next_step,
        "steps": all_steps,
        "current_step": all_steps[current],
        "max_step": max_step,
    }


def registration_opened_context(request):
    try:
        start = request.REGISTRATION_START
        end = request.REGISTRATION_END
    except AttributeError:
        return {}
    now = timezone.now()
    minutes_spent = int((now - start).total_seconds() / 60)
    minutes_total = int((end - start).total_seconds() / 60)
    return {
        "registration_opened": request.REGISTRATION_OPENED,
        "registration_phase": request.PHASE,
        "registration_start": start,
        "registration_end": end,
        "registration_past": start <= end <= now,
        "registration_due": now <= start <= end,
        "minutes_spent": minutes_spent,
        "minutes_total": minutes_total,
    }


def activities_context(request):
    activities = []
    for slug, label in settings.KEPCHUP_ACTIVITY_TYPES:
        activities.append((label, Activity.objects.visible().filter(type=slug).order_by("name")))
    return {"activities_types": activities}


def tenants_context(request):
    user = request.user

    if user.is_authenticated and user.is_manager or user.is_superuser or user.is_staff:
        return {"tenants": YearTenant.objects.all()}
    if user.is_authenticated and user.is_kepchup_staff:
        tenants = []
        with connection.cursor() as cursor:
            for tenant in YearTenant.objects.all():
                cursor.execute(
                    "SELECT id FROM {}.activities_coursesinstructors WHERE instructor_id=%s".format(
                        tenant.schema_name
                    ),
                    [user.id],
                )
                row = cursor.fetchone()
                if row:
                    tenants.append(tenant)
        return {"tenants": tenants}
    return {}


def kepchup_context(request):
    return {
        "AVS_HIDDEN": "avs" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "BIB_NUMBER_HIDDEN": "bib_number" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "BIRTH_DATE_HIDDEN": "birth_date" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "BUILDING_HIDDEN": "building" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "EMERGENCY_NUMBER_HIDDEN": "emergency_number" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "FIRST_NAME_HIDDEN": "first_name" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "ID_LAGAPEO_HIDDEN": "id_lagapeo" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "LANGUAGE_HIDDEN": "language" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "NATIONALITY_HIDDEN": "nationality" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "OTHER_SCHOOL_HIDDEN": "other_school" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "SCHOOL_YEAR_HIDDEN": "school_year" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "SCHOOL_HIDDEN": "school" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "SEX_HIDDEN": "sex" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "TEACHER_HIDDEN": "teacher" in settings.KEPCHUP_CHILDREN_HIDDEN_FIELDS,
        "AVS_EDITABLE": "avs" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "BIB_NUMBER_EDITABLE": "bib_number" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "BIRTH_DATE_EDITABLE": "birth_date" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "BUILDING_EDITABLE": "building" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "EMERGENCY_NUMBER_EDITABLE": "emergency_number" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "EMERGENCY_NUMBER_MANDATORY": settings.KEPCHUP_EMERGENCY_NUMBER_MANDATORY,
        "FIRST_NAME_EDITABLE": "first_name" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "ID_LAGAPEO_EDITABLE": "id_lagapeo" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "LANGUAGE_EDITABLE": "language" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "LAST_NAME_EDITABLE": "last_name" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "LIMIT_BY_AGE": settings.KEPCHUP_LIMIT_BY_AGE,
        "LIMIT_BY_SCHOOL_YEAR": settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR,
        "SCHOOL_YEAR_MANDATORY": settings.KEPCHUP_SCHOOL_YEAR_MANDATORY,
        "NATIONALITY_EDITABLE": "nationality" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "OTHER_SCHOOL_EDITABLE": "other_school" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "SCHOOL_YEAR_EDITABLE": "school_year" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "SCHOOL_EDITABLE": "school" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "SEX_EDITABLE": "sex" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "TEACHER_EDITABLE": "teacher" not in settings.KEPCHUP_CHILDREN_UNEDITABLE_FIELDS,
        "REGISTRATION_EXPIRE_MINUTES": settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES,
        "USE_ABSENCES": settings.KEPCHUP_USE_ABSENCES,
        "ABSENCES_RELATE_TO_ACTIVITIES": settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES,
        "ABSENCES_ORDER_ASC": settings.KEPCHUP_ABSENCES_ORDER_ASC,
        "USE_BUILDINGS": settings.KEPCHUP_USE_BUILDINGS,
        "IMPORT_CHILDREN": settings.KEPCHUP_IMPORT_CHILDREN,
        "PREFILL_YEARS_WITH_TEACHERS": settings.KEPCHUP_PREFILL_YEARS_WITH_TEACHERS,
        "NO_PAYMENT": settings.KEPCHUP_NO_PAYMENT,
        "PAYMENT_METHOD": settings.KEPCHUP_PAYMENT_METHOD,
        "DISPLAY_FREE_WHEN_PRICE_IS_0": settings.KEPCHUP_DISPLAY_FREE_WHEN_PRICE_IS_0,
        "USE_DIFFERENTIATED_PRICES": settings.KEPCHUP_USE_DIFFERENTIATED_PRICES,
        "LOCAL_ZIPCODES": settings.KEPCHUP_LOCAL_ZIPCODES,
        "NO_TERMS": settings.KEPCHUP_NO_TERMS,
        "NO_SSF": settings.KEPCHUP_NO_SSF,
        "CHILD_SCHOOL": settings.KEPCHUP_CHILD_SCHOOL,
        "CHILD_SCHOOL_DISPLAY_OTHER": settings.KEPCHUP_CHILD_SCHOOL_DISPLAY_OTHER,
        "DISPLAY_PARENT_CITY": settings.KEPCHUP_DISPLAY_PARENT_CITY,
        "DISPLAY_PARENT_EMAIL": settings.KEPCHUP_DISPLAY_PARENT_EMAIL,
        "DISPLAY_PARENT_PHONE": settings.KEPCHUP_DISPLAY_PARENT_PHONE,
        "CALENDAR_DISPLAY_DATES": settings.KEPCHUP_CALENDAR_DISPLAY_DATES,
        "CALENDAR_DISPLAY_COURSE_NAMES": settings.KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES,
        "CALENDAR_HIDDEN_DAYS": settings.KEPCHUP_CALENDAR_HIDDEN_DAYS,
        "ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE": settings.KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE,
        "BIB_NUMBERS": settings.KEPCHUP_BIB_NUMBERS,
        "FICHE_SALAIRE_MONTREUX": settings.KEPCHUP_FICHE_SALAIRE_MONTREUX,
        "REGISTRATION_LEVELS": settings.KEPCHUP_REGISTRATION_LEVELS,
        "DISPLAY_CAR_NUMBER": settings.KEPCHUP_DISPLAY_CAR_NUMBER,
        "DISPLAY_REGISTRATION_NOTE": settings.KEPCHUP_DISPLAY_REGISTRATION_NOTE,
        "DISPLAY_NUMBER_OF_SESSIONS": settings.KEPCHUP_DISPLAY_NUMBER_OF_SESSIONS,
        "PROTOCOL": settings.DEBUG and "http://" or "https://",
        "REGISTER_ACCOUNTS_AT_ANY_TIME": settings.KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME,
        "EXPLICIT_SESSION_DATES": settings.KEPCHUP_EXPLICIT_SESSION_DATES,
        "NO_EXTRAS": settings.KEPCHUP_NO_EXTRAS,
        "USE_SSO": settings.KEPCHUP_USE_SSO,
        "USE_APPOINTMENTS": settings.KEPCHUP_USE_APPOINTMENTS,
        "DISPLAY_LAGAPEO": settings.KEPCHUP_DISPLAY_LAGAPEO,
        "DISPLAY_OVERLAP_HELP": settings.KEPCHUP_DISPLAY_OVERLAP_HELP,
        "CAN_DELETE_CHILD": settings.KEPCHUP_CAN_DELETE_CHILD,
        "INSTRUCTORS_CAN_REMOVE_REGISTRATIONS": settings.KEPCHUP_INSTRUCTORS_CAN_REMOVE_REGISTRATIONS,
        "ENABLE_ALLOCATION_ACCOUNTS": settings.KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS,
        "ENABLE_TEACHER_MANAGEMENT": settings.KEPCHUP_ENABLE_TEACHER_MANAGEMENT,
        "ENABLE_PAYROLLS": settings.KEPCHUP_ENABLE_PAYROLLS,
        "ENABLE_WAITING_LISTS": settings.KEPCHUP_ENABLE_WAITING_LISTS,
        "DASHBOARD_SHOW_CHILDREN_STATS": settings.KEPCHUP_DASHBOARD_SHOW_CHILDREN_STATS,
        "DASHBOARD_SHOW_FAMILY_STATS": settings.KEPCHUP_DASHBOARD_SHOW_FAMILY_STATS,
        "USE_BLACKLISTS": settings.KEPCHUP_USE_BLACKLISTS,
        "INSTRUCTORS_DISPLAY_EXTERNAL_ID": settings.KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID,
        "INSTRUCTORS_CAN_EDIT_EXTERNAL_ID": settings.KEPCHUP_INSTRUCTORS_CAN_EDIT_EXTERNAL_ID,
        "ALTERNATIVE_ABOUT_LABEL": settings.KEPCHUP_ALTERNATIVE_ABOUT_LABEL,
        "ALTERNATIVE_CHILDREN_LABEL": settings.KEPCHUP_ALTERNATIVE_CHILDREN_LABEL,
        "ALTERNATIVE_ACTIVITIES_LABEL": settings.KEPCHUP_ALTERNATIVE_ACTIVITIES_LABEL,
        "ALTERNATIVE_CONFIRM_LABEL": settings.KEPCHUP_ALTERNATIVE_CONFIRM_LABEL,
        "ALTERNATIVE_BILLING_LABEL": settings.KEPCHUP_ALTERNATIVE_BILLING_LABEL,
        "YEAR_NAMES": settings.KEPCHUP_YEAR_NAMES,
    }


def dynamic_preferences_context(request):
    global_preferences = global_preferences_registry.manager()
    try:
        start = make_aware(global_preferences["phase__OTHER_START_REGISTRATION"], get_default_timezone())
    except IndexError:
        start = None
    except ValueError:
        start = global_preferences["phase__OTHER_START_REGISTRATION"]
    try:
        end = make_aware(global_preferences["phase__OTHER_END_REGISTRATION"], get_default_timezone())
    except IndexError:
        end = None
    except ValueError:
        end = global_preferences["phase__OTHER_END_REGISTRATION"]
    if start > now():
        other_phase = 1
    elif end > now():
        other_phase = 2
    else:
        other_phase = 3
    return {
        "site_name": global_preferences["site__SITE_NAME"],
        "preferences_period_name": global_preferences["PERIOD_NAME"],
        "preference_other_instance_start_registration": global_preferences["phase__OTHER_START_REGISTRATION"],
        "preference_other_instance_end_registration": global_preferences["phase__OTHER_END_REGISTRATION"],
        "other_instance_phase": other_phase,
        "other_instance_started_registrations": other_phase == 2,
        "MAX_REGISTRATIONS_PER_CHILD": global_preferences["MAX_REGISTRATIONS"],
    }
