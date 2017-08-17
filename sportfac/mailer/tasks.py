from __future__ import absolute_import
from tempfile import mkdtemp
import os
import shutil

from django.core.mail import EmailMessage
from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger

from activities.models import Course
from profiles.models import FamilyUser
from .pdfutils import get_ssf_decompte_heures, CourseParticipants, CourseParticipantsPresence, MyCourses
from .models import Attachment

logger = get_task_logger(__name__)


@shared_task
def send_mail(subject, message, from_email, recipients, reply_to, bcc=None, attachments=None):
    if bcc is None:
        bcc = []
    if attachments is None:
        attachments = []
    else:
        attachments = Attachment.objects.filter(pk__in=attachments)
    logger.debug("Sending email to %s" % recipients)
    email = EmailMessage(subject=subject,
                         body=message,
                         from_email=from_email,
                         to=recipients,
                         bcc=bcc,
                         reply_to=reply_to)
    for attachment in attachments:
        email.attach_file(attachment.file.path)

    return email.send(fail_silently=not settings.DEBUG)


@shared_task
def send_instructors_email(subject, message, from_email, course_pk, reply_to, bcc=None):
    logger.debug("Forging email to instructors of course #%s" % course_pk)
    if bcc is None:
        bcc = []
    else:
        bcc = FamilyUser.objects.filter(pk__in=bcc)

    course = Course.objects.get(pk=course_pk)
    for instructor in course.instructors.all():
        recipients = (instructor.get_from_address(), )
        email = EmailMessage(subject=subject,
                             body=message,
                             from_email=from_email,
                             to=recipients,
                             bcc=bcc,
                             reply_to=reply_to)
        logger.debug("Message created")

        if not settings.KEPCHUP_NO_SSF:
            filepath = get_ssf_decompte_heures(course, instructor)
            filename = 'E_SSF_decompte_heures_%s_%s.pdf' % (
                instructor.first_name, instructor.last_name)
            email.attach(filename, open(filepath).read(), 'application/pdf')
            logger.debug("Decompte.pdf attached")

        tempdir = mkdtemp()
        filename = '%s-participants.pdf' % course.number
        filepath = os.path.join(tempdir, filename)
        cp_generator = CourseParticipants({'course': course})
        cp_generator.render_to_pdf(filepath)
        email.attach(filename, open(filepath).read(), 'application/pdf')
        logger.debug("Participants.pdf attached")

        if settings.KEPCHUP_SEND_PRESENCE_LIST:
            filename = '%s-presences.pdf' % course.number
            filepath = os.path.join(tempdir, filename)
            cp_generator = CourseParticipantsPresence({'course': course})
            cp_generator.render_to_pdf(filepath)
            email.attach(filename, open(filepath).read(), 'application/pdf')
            logger.debug("Presences.pdf attached")

        filename = 'mes_cours.pdf'
        filepath = os.path.join(tempdir, filename)
        cp_generator = MyCourses({'instructor': instructor,
                                  'courses': Course.objects.filter(instructors=instructor)})
        cp_generator.render_to_pdf(filepath)
        email.attach(filename, open(filepath).read(), 'application/pdf')
        logger.debug("Courses.pdf attached")

        for additional_doc in settings.KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS:
            filepath = os.path.join(settings.STATIC_ROOT, additional_doc)
            email.attach_file(filepath)

        shutil.rmtree(tempdir)
        logger.debug("Email forged, sending...")
        email.send(fail_silently=not(settings.DEBUG))
