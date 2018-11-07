from django.conf import settings
from django.contrib.sites.models import Site
from django.db import connection
from django.template.loader import render_to_string
from django.utils import translation

from celery import shared_task

from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain, YearTenant
from mailer.tasks import send_mail
from profiles.models import FamilyUser
from registrations.models import Bill
from sportfac.decorators import respect_language


@shared_task
@respect_language
def send_confirmation(user_pk, bill_pk, tenant_pk=None):
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
    current_site = Site.objects.get_current()

    context = {
        'user': user,
        'registrations': registrations,
        'bill': bill,
        'iban': global_preferences['payment__IBAN'],
        'signature': global_preferences['email__SIGNATURE'],
        'payment': not settings.KEPCHUP_NO_PAYMENT,
        'site_name': current_site.name,
        'site_url': settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain
    }
    subject = render_to_string('registrations/confirmation_mail_subject.txt', context=context)

    body = render_to_string('registrations/confirmation_mail.txt', context=context)
    send_mail.delay(
        subject=subject, message=body,
        from_mail=global_preferences['email__FROM_MAIL'],
        recipients=[user.get_email_string()],
        reply_to=[global_preferences['email__REPLY_TO_MAIL']]
    )

