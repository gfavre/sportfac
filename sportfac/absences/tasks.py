# -*- coding: utf-8 -*-
from __future__ import absolute_import
import datetime

from django.contrib.sites.models import Site
from django.conf import settings
from django.db import connection
from django.utils import timezone
from django.template import loader

from celery import shared_task
from celery.utils.log import get_task_logger

from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain

from mailer.tasks import send_mail
from sportfac.decorators import respects_language
from .models import Absence


logger = get_task_logger(__name__)


@shared_task
@respects_language
def notify_absences():
    current_domain = Domain.objects.filter(is_current=True).first()
    connection.set_tenant(current_domain.tenant)

    now = timezone.now()
    preferences = global_preferences_registry.manager()
    offset_days = preferences['ABSENCE_DELAY']
    absences = Absence.absent.filter(notification_sent=False,
                                     session__date__lt=now - datetime.timedelta(days=offset_days))
    logger.info('%i absences to notify' % absences.count())
    current_site = Site.objects.get_current()
    base_context = {
        'signature': preferences['email__SIGNATURE'],
        'site_name': current_site.name,
        'site_url': settings.debug and 'http://' + current_site.domain or 'https://' + current_site.domain
    }
    subject_tmpl = loader.get_template('mailer/absence_notification_subject.txt')
    body_tmpl = loader.get_template('mailer/absence_notification.txt')
    from_email = preferences['email__FROM_MAIL']
    reply_to = preferences['email__REPLY_TO_MAIL']

    for absence in absences:
        context = base_context.copy()
        context['child'] = absence.child
        context['course'] = absence.session.course
        context['session'] = absence.session
        subject = subject_tmpl.render(context)
        body = body_tmpl.render(context)
        recipients = [absence.child.family.get_email_string()]
        logger.debug('Forging email')
        logger.debug('Subject: ' + subject)
        logger.debug('Body: ' + body)
        send_mail.s(subject, body, from_email, recipients, reply_to)
        absence.notification_sent = True
        absence.save()
