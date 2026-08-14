import logging

from celery import shared_task
from django.conf import settings
from django.db import connection
from django.utils import translation

from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain
from backend.models import YearTenant
from mailer.tasks import send_mail
from mailer.utils import render_email_content

from .models import Appointment


__all__ = ["send_confirmation_mail"]
logger = logging.getLogger()


@shared_task
def send_confirmation_mail(appointment_pks, tenant_pk=None, user=None, language=settings.LANGUAGE_CODE):
    cur_lang = translation.get_language()
    try:
        translation.activate(language)
        if tenant_pk:
            tenant = YearTenant.objects.get(pk=tenant_pk)
            connection.set_tenant(tenant)
        else:
            current_domain = Domain.objects.filter(is_current=True).first()
            connection.set_tenant(current_domain.tenant)

        global_preferences = global_preferences_registry.manager()
        appointments = Appointment.objects.filter(pk__in=appointment_pks)
        context = {
            "appointments": appointments,
            "signature": global_preferences["email__SIGNATURE"],
            "user": user,
        }
        subject = render_email_content("appointments/confirmation_mail_subject.txt", extra_context=context)
        body = render_email_content("appointments/confirmation_mail.txt", extra_context=context)
        recipients = list({appointment.email for appointment in appointments})

        logger.info(f"Send appointment confirmation to: {recipients}")
        send_mail.delay(
            subject=subject,
            message=body,
            from_email=global_preferences["email__FROM_MAIL"],
            recipients=recipients,
            reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
        )
    finally:
        translation.activate(cur_lang)
