from __future__ import absolute_import
from tempfile import  mkdtemp
import os, shutil

from django.core.mail import send_mail as django_send_mail
from django.core.mail import EmailMessage
from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger

from .pdfutils import get_ssf_decompte_heures, CourseParticipants, CourseParticipantsPresence, MyCourses
from activities.models import Course



logger = get_task_logger(__name__)


@shared_task
def send_mail(subject, message, from_email, recipients):    
    logger.debug("Sending email to %s" % recipients)
    return django_send_mail(subject=subject, 
                            message=message, 
                            from_email=from_email, 
                            recipient_list=recipients)

@shared_task
def send_responsible_email(subject, message, from_email, course_pk):
    logger.debug("Forging email to responsible of course #%s" % course_pk)
 
    course = Course.objects.get(pk=course_pk)
    recipients = (course.responsible.get_from_address(), )
    email = EmailMessage(subject=subject,
                         body=message,
                         from_email=from_email,
                         to=recipients)
    logger.debug("Message created" % course_pk)

    filepath = get_ssf_decompte_heures(course)
    filename = 'E_SSF_decompte_heures_%s_%s.pdf' % (course.responsible.first_name, 
                                                    course.responsible.last_name)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug("Decompte.pdf attached")
    tempdir = mkdtemp()
    
    filename = '%s - participants.pdf' % course.number
    filepath = os.path.join(tempdir, filename)
    cp_generator = CourseParticipants({'course': course})
    cp_generator.render_to_pdf(filepath)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug("Participants.pdf attached")

    
    filename = '%s - presences.pdf' % course.number
    filepath = os.path.join(tempdir, filename)
    cp_generator = CourseParticipantsPresence({'course': course})
    cp_generator.render_to_pdf(filepath)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug("Presences.pdf attached")


    filename = '%s - tous les cours.pdf' % course.responsible.full_name
    filepath = os.path.join(tempdir, filename)
    cp_generator = MyCourses({'responsible': course.responsible, 
                              'courses':Course.objects.filter(responsible=course.responsible)})
    cp_generator.render_to_pdf(filepath)
    email.attach(filename, open(filepath).read(), 'application/pdf')
    logger.debug("Courses.pdf attached")

    shutil.rmtree(tempdir)
    logger.debug("Email forged, sending...")
    return email.send()