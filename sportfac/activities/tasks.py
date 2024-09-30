from functools import wraps

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import connection
from django.template.loader import render_to_string
from django.utils import timezone, translation

from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain, YearTenant
from celery import shared_task
from celery.utils.log import get_task_logger
from mailer.tasks import send_mail

from .models import Course


logger = get_task_logger(__name__)


def tenant_and_language_switcher(language=settings.LANGUAGE_CODE):
    """
    Decorator to switch language and tenant context for the function.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cur_lang = translation.get_language()
            tenant_pk = kwargs.get("tenant_pk")

            try:
                # Activate the desired language
                translation.activate(language)

                # Set the tenant based on tenant_pk
                if tenant_pk:
                    tenant = YearTenant.objects.get(pk=tenant_pk)
                    connection.set_tenant(tenant)
                else:
                    current_domain = Domain.objects.filter(is_current=True).first()
                    connection.set_tenant(current_domain.tenant)

                # Execute the wrapped function
                return func(*args, **kwargs)
            finally:
                # Restore the original language
                translation.activate(cur_lang)

        return wrapper

    return decorator


@shared_task
@tenant_and_language_switcher(language=settings.LANGUAGE_CODE)
def send_places_available_reminder(course_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
    if not settings.KEPCHUP_ENABLE_WAITING_LISTS:
        return False
    course = Course.objects.get(pk=course_pk)
    current_site = Site.objects.get_current()
    global_preferences = global_preferences_registry.manager()
    context = {
        "course": course,
        "available_places": course.available_places,
        "waiting_list": course.waiting_slots.count(),
        "site_name": global_preferences["site__SITE_NAME"],
        "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
    }
    subject = render_to_string("activities/places-available-reminder_subject.txt", context=context)
    body = render_to_string("activities/places-available-reminder.txt", context=context)
    send_mail.delay(
        subject=subject,
        message=body,
        from_email=global_preferences["email__FROM_MAIL"],
        recipients=[global_preferences["email__CONTACT_MAIL"]],
        reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
    )
    course.places_available_reminder_sent_on = timezone.now()
    course.save()
    return True
