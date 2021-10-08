# -*- coding:utf-8 -*-
from __future__ import absolute_import
import os
import shutil
from smtplib import SMTPException
from tempfile import mkdtemp

from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone

from celery.utils.log import get_task_logger

from activities.models import Course
from profiles.models import FamilyUser
from sportfac.celery import app
from .pdfutils import get_ssf_decompte_heures, CourseParticipants, CourseParticipantsPresence, MyCourses
from .models import Attachment


logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=6)
def send_mail(self, subject, message, from_email, recipients, reply_to, bcc=None, attachments=None,
              update_bills=False, recipient_pk=None):
    if bcc is None:
        bcc = []
    if attachments is None:
        attachments = []
    else:
        attachments = Attachment.objects.filter(pk__in=attachments)
    logger.debug(u"Sending email to %s" % recipients)
    email = EmailMessage(subject=subject,
                         body=message,
                         from_email=from_email,
                         to=recipients,
                         bcc=bcc,
                         reply_to=reply_to)
    for attachment in attachments:
        email.attach_file(attachment.file.path)
    try:
        email.send()
        logger.info(u'Sent email "{}" to {}'.format(subject, recipients))
        if update_bills and recipient_pk:
            try:
                recipient = FamilyUser.objects.get(pk=recipient_pk)
                for bill in recipient.bills.waiting():
                    bill.reminder_sent = True
                    bill.reminder_sent_date = timezone.now()
                    bill.save()
                    logger.debug(u'Updated bill sent status for {}'.format(bill.id))
            except FamilyUser.DoesNotExist:
                logger.warning(u'No user found for pk={} email={}'.format(recipient_pk, recipients[0]))
    except SMTPException as smtp_exc:
        logger.error(u"Message {} to {} could not be sent: {}".format(subject, recipients, smtp_exc.message))
        # 5s for first retry, 25 for second, 2mn for third ~10mn for fourth, 52mn for fifth
        self.retry(countdown=5 ** self.request.retries)


@app.task(bind=True, max_retries=6)
def send_instructors_email(self, course_pk, instructor_pk, subject, message, from_email, reply_to, bcc=None):
    logger.debug(u"Forging email to instructors of course #%s" % course_pk)
    if bcc is None:
        bcc = []
    course = Course.objects.get(pk=course_pk)
    instructor = FamilyUser.objects.get(pk=instructor_pk)

    email = EmailMessage(subject=subject,
                         body=message,
                         from_email=from_email,
                         to=[instructor.get_email_string()],
                         bcc=bcc,
                         reply_to=reply_to)
    logger.debug("Message created")

    tempdir = mkdtemp()

    filename = '%s-participants.pdf' % course.number
    filepath = os.path.join(tempdir, filename)
    cp_generator = CourseParticipants({'course': course})
    cp_generator.render_to_pdf(filepath)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug("Participants.pdf attached")
    filename = 'mes_cours.pdf'
    filepath = os.path.join(tempdir, filename)
    cp_generator = MyCourses({'instructor': instructor,
                              'courses': Course.objects.filter(instructors=instructor)})
    cp_generator.render_to_pdf(filepath)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug(u"Courses.pdf attached")

    if not (settings.KEPCHUP_NO_SSF or settings.KEPCHUP_FICHE_SALAIRE_MONTREUX):
        filepath = get_ssf_decompte_heures(course, instructor)
        filename = 'SSF_decompte_moniteur_%s_%s.pdf' % (
            instructor.first_name, instructor.last_name)
        email.attach(filename, open(filepath).read(), 'application/pdf')
        logger.debug("Decompte.pdf attached")

    if settings.KEPCHUP_SEND_PRESENCE_LIST:
        filename = '%s-presences.pdf' % course.number
        filepath = os.path.join(tempdir, filename)
        cp_generator = CourseParticipantsPresence({'course': course})
        cp_generator.render_to_pdf(filepath)
        email.attach(filename, open(filepath).read(), 'application/pdf')
        logger.debug(u"Presences.pdf attached")

    for additional_doc in settings.KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS:
        filepath = os.path.join(settings.STATIC_ROOT, additional_doc)
        email.attach_file(filepath)

    logger.debug(u"Email forged, sending...")
    try:
        email.send()
        logger.info(u'Sent instructor email to {}'.format(instructor.get_email_string()))
    except SMTPException as smtp_exc:
        logger.error(u"Message {} to {} could not be sent: {}".format(subject, [instructor.get_email_string()],
                                                                      smtp_exc.message))
        # 5s for first retry, 25 for second, 2mn for third ~10mn for fourth, 52mn for fifth
        self.retry(countdown=5 ** self.request.retries)
    finally:
        shutil.rmtree(tempdir)
