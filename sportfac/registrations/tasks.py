from datetime import timedelta
import tempfile

from django.conf import settings
from django.contrib.sites.models import Site
from django.db import connection
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.timezone import now

from celery import shared_task

from appointments.models import Appointment
from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain, YearTenant
from mailer.tasks import send_mail
from profiles.models import FamilyUser
from registrations.models import Bill, Registration
from waiting_slots.models import WaitingSlot


@shared_task
def send_bill_confirmation(user_pk, bill_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
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

        user = FamilyUser.objects.get(pk=user_pk)
        bill = Bill.objects.get(pk=bill_pk)
        registrations = bill.registrations.all()
        waiting_slots = WaitingSlot.objects.filter(child__family=user)
        current_site = Site.objects.get_current()
        context = {
            'appointments': None,
            'user': user,
            'registrations': registrations,
            'waiting_slots': waiting_slots,
            'bill': bill,
            'iban': global_preferences['payment__IBAN'],
            'signature': global_preferences['email__SIGNATURE'],
            'payment': not settings.KEPCHUP_NO_PAYMENT,
            'site_name': current_site.name,
            'site_url': settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain
        }
        if settings.KEPCHUP_USE_APPOINTMENTS:
            context['appointments'] = Appointment.objects.filter(family=user)

        subject = render_to_string('registrations/confirmation_bill_mail_subject.txt', context=context)
        body = render_to_string('registrations/confirmation_bill_mail.txt', context=context)

        attachments = []
        if bill.is_wire_transfer:
            tempdir = tempfile.mkdtemp()
        send_mail.delay(
            subject=subject, message=body,
            from_email=global_preferences['email__FROM_MAIL'],
            recipients=[user.get_email_string()],
            reply_to=[global_preferences['email__REPLY_TO_MAIL']]
        )
        registrations.update(confirmation_sent_on=now())
    finally:
        translation.activate(cur_lang)


@shared_task
def send_confirmation(user_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
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

        user = FamilyUser.objects.get(pk=user_pk)
        registrations = Registration.objects.filter(child__family=user, confirmation_sent_on__isnull=True)
        waiting_slots = WaitingSlot.objects.filter(child__family=user)

        current_site = Site.objects.get_current()
        context = {
            'appointments': None,
            'user': user,
            'registrations': registrations,
            'waiting_slots': waiting_slots,
            'signature': global_preferences['email__SIGNATURE'],
            'site_name': current_site.name,
            'site_url': settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain
        }

        subject = render_to_string('registrations/confirmation_mail_subject.txt', context=context)

        body = render_to_string('registrations/confirmation_mail.txt', context=context)
        send_mail.delay(
            subject=subject, message=body,
            from_email=global_preferences['email__FROM_MAIL'],
            recipients=[user.get_email_string()],
            reply_to=[global_preferences['email__REPLY_TO_MAIL']]
        )
        registrations.update(confirmation_sent_on=now())
    finally:
        translation.activate(cur_lang)


@shared_task
def cancel_expired_registrations():
    if not settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES:
        return
    current_domain = Domain.objects.filter(is_current=True).first()
    connection.set_tenant(current_domain.tenant)
    registrations = Registration.objects.filter(
        status='waiting',
        created__lte=(now() - timedelta(minutes=settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES))
    )
    for registration in registrations:
        registration.cancel(reason=Registration.REASON.expired)
        registration.save()
