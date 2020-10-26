# -*- coding: utf-8 -*-
import logging

from django.conf import settings
from django.db import connection
from django.template.loader import render_to_string
from django.utils import translation

from celery import shared_task


from backend.models import Domain, YearTenant
from backend.dynamic_preferences_registry import global_preferences_registry
from mailer.tasks import send_mail
from .models import Appointment


__all__ = ['send_confirmation_mail']
logger = logging.getLogger()


@shared_task
def send_confirmation_mail(appointment_pks, tenant_pk=None, language=settings.LANGUAGE_CODE):
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
            'appointments': appointments,
            'signature': global_preferences['email__SIGNATURE'],
        }
        subject = render_to_string('appointments/confirmation_mail_subject.txt', context=context)
        body = render_to_string('appointments/confirmation_mail.txt', context=context)
        recipients = set(appointment.email for appointment in appointments)

        logger.info('Send appointment confirmation to: {}'.format(recipients))
        send_mail.delay(
            subject=subject, message=body,
            from_email=global_preferences['email__FROM_MAIL'],
            recipients=recipients,
            reply_to=[global_preferences['email__REPLY_TO_MAIL']]
        )
    finally:
        translation.activate(cur_lang)
