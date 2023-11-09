from datetime import timedelta

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.db import connection
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.timezone import now

from anymail.exceptions import AnymailRecipientsRefused
from appointments.models import Appointment
from backend.dynamic_preferences_registry import global_preferences_registry
from backend.models import Domain, YearTenant
from celery import shared_task
from celery.utils.log import get_task_logger
from mailer.tasks import send_mail
from profiles.models import FamilyUser
from registrations.models import Bill, Registration


logger = get_task_logger(__name__)


@shared_task
def send_bill_confirmation(user_pk, bill_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
    from waiting_slots.models import WaitingSlot

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
            "appointments": None,
            "user": user,
            "registrations": registrations,
            "waiting_slots": waiting_slots,
            "bill": bill,
            "iban": global_preferences["payment__IBAN"],
            "signature": global_preferences["email__SIGNATURE"],
            "payment": not settings.KEPCHUP_NO_PAYMENT,
            "site_name": current_site.name,
            "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
        }
        if settings.KEPCHUP_USE_APPOINTMENTS:
            context["appointments"] = Appointment.objects.filter(family=user)

        subject = render_to_string("registrations/confirmation_bill_mail_subject.txt", context=context)
        body = render_to_string("registrations/confirmation_bill_mail.txt", context=context)

        send_mail.delay(
            subject=subject,
            message=body,
            from_email=global_preferences["email__FROM_MAIL"],
            recipients=[user.get_email_string()],
            reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
        )
        registrations.update(confirmation_sent_on=now())
    finally:
        translation.activate(cur_lang)


@shared_task
def send_confirmation(user_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
    from waiting_slots.models import WaitingSlot

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
            "appointments": None,
            "user": user,
            "registrations": registrations,
            "waiting_slots": waiting_slots,
            "signature": global_preferences["email__SIGNATURE"],
            "site_name": current_site.name,
            "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
        }

        subject = render_to_string("registrations/confirmation_mail_subject.txt", context=context)

        body = render_to_string("registrations/confirmation_mail.txt", context=context)
        send_mail.delay(
            subject=subject,
            message=body,
            from_email=global_preferences["email__FROM_MAIL"],
            recipients=[user.get_email_string()],
            reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
        )
        registrations.update(confirmation_sent_on=now())
    finally:
        translation.activate(cur_lang)


@shared_task()
def send_confirm_from_waiting_list(registration_pk, tenant_pk=None, language=settings.LANGUAGE_CODE):
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

        registration = Registration.objects.get(pk=registration_pk)
        user = registration.child.family

        current_site = Site.objects.get_current()
        context = {
            "user": user,
            "registration": registration,
            "bill": registration.bill,
            "signature": global_preferences["email__SIGNATURE"],
            "site_name": current_site.name,
            "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
        }

        subject = render_to_string("waiting_slots/confirm_from_waiting_list_mail_subject.txt", context=context)

        body = render_to_string("waiting_slots/confirm_from_waiting_list_mail_body.txt", context=context)
        send_mail.delay(
            subject=subject,
            message=body,
            from_email=global_preferences["email__FROM_MAIL"],
            recipients=[user.get_email_string()],
            reply_to=[global_preferences["email__REPLY_TO_MAIL"]],
        )
    finally:
        translation.activate(cur_lang)


@shared_task
def cancel_expired_registrations():
    if not settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES:
        return
    current_domain = Domain.objects.filter(is_current=True).first()
    connection.set_tenant(current_domain.tenant)
    expired_invoices = Bill.objects.filter(
        status=Bill.STATUS.waiting,
        modified__lte=(now() - timedelta(minutes=settings.KEPCHUP_REGISTRATION_EXPIRE_MINUTES)),
    )
    for invoice in expired_invoices:
        invoice.cancel()


@shared_task
def generate_invoice_pdf(bill_id):
    bill = Bill.objects.get(pk=bill_id)
    bill.generate_pdf()


@shared_task
def send_invoice_pdf(bill_pk, tenant_pk=None):
    if tenant_pk:
        tenant = YearTenant.objects.get(pk=tenant_pk)
        connection.set_tenant(tenant)
    else:
        current_domain = Domain.objects.filter(is_current=True).first()
        connection.set_tenant(current_domain.tenant)

    global_preferences = global_preferences_registry.manager()
    if not global_preferences["email__ACCOUNTANT_MAIL"]:
        return
    bill = Bill.objects.get(pk=bill_pk)
    if not bill.pdf:
        bill.generate_pdf()
        bill.refresh_from_db()

    current_site = Site.objects.get_current()
    context = {
        "bill": bill,
        "signature": global_preferences["email__SIGNATURE"],
        "payment": not settings.KEPCHUP_NO_PAYMENT,
        "site_name": current_site.name,
        "site_url": settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain,
    }
    subject = (
        render_to_string("registrations/accountant_bill_mail_subject.txt", context=context).replace("\n", "").strip()
    )
    body = render_to_string("registrations/accountant_bill_mail.txt", context=context)

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=global_preferences["email__FROM_MAIL"],
        to=[email.strip() for email in global_preferences["email__ACCOUNTANT_MAIL"].split(",")],
        bcc=[],
    )
    try:
        email.attach_file(bill.pdf.path)
    except ValueError as exc:
        logger.exception("Could not attach pdf to accountant email", exc_info=exc)
        return
    try:
        email.send()
        logger.info("Sent accountant email to {}".format(global_preferences["email__ACCOUNTANT_MAIL"]))
    except AnymailRecipientsRefused as exc:
        logger.error(
            "Message {} to {} could not be sent: {}".format(subject, global_preferences["email__ACCOUNTANT_MAIL"], exc)
        )
