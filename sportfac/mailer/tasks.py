import os
import shutil
from smtplib import SMTPException
from tempfile import mkdtemp

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from anymail.exceptions import AnymailRecipientsRefused
from celery.utils.log import get_task_logger

from activities.models import Course
from profiles.models import FamilyUser
from sportfac.celery import app
from .models import Attachment
from .pdfutils import CourseParticipants, CourseParticipantsPresence, MyCourses, get_ssf_decompte_heures


logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=6)
def send_mail(
    self,
    subject,
    message,
    from_email,
    recipients,
    reply_to,
    bcc=None,
    attachments=None,
    update_bills=False,
    recipient_pk=None,
):
    logger.warning("LEVEL is %s", logger.getEffectiveLevel())
    logger.debug("Forging email to %s" % recipients)
    if bcc is None:
        bcc = []
    if attachments is None:
        attachments = []
    else:
        attachments = Attachment.objects.filter(pk__in=attachments)
    logger.debug("Sending email to %s" % recipients)
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipients,
        bcc=bcc,
        reply_to=reply_to,
    )
    for attachment in attachments:
        email.attach_file(attachment.file.path)
    try:
        email.send()
        logger.info(f'Sent email "{subject}" to {recipients}')
        if update_bills and recipient_pk:
            try:
                recipient = FamilyUser.objects.get(pk=recipient_pk)
                for bill in recipient.bills.waiting():
                    bill.reminder_sent = True
                    bill.reminder_sent_date = timezone.now()
                    bill.save()
                    logger.debug(f"Updated bill sent status for {bill.id}")
            except FamilyUser.DoesNotExist:
                logger.warning(f"No user found for pk={recipient_pk} email={recipients[0]}")
    except AnymailRecipientsRefused as exc:
        logger.warning(f"Message {subject} to {recipients} could not be sent: {exc}")

    except SMTPException as smtp_exc:
        logger.warning(f"Message {subject} to {recipients} could not be sent: {smtp_exc}")
        # 5s for first retry, 25 for second, 2mn for third ~10mn for fourth, 52mn for fifth
        self.retry(countdown=5**self.request.retries)


@app.task(bind=True, max_retries=6)
def send_instructors_email(self, course_pk, instructor_pk, subject, message, from_email, reply_to, bcc=None):
    logger.debug("Forging email to instructors of course #%s" % course_pk)
    if bcc is None:
        bcc = []
    course = Course.objects.get(pk=course_pk)
    instructor = FamilyUser.objects.get(pk=instructor_pk)

    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=[instructor.get_email_string()],
        bcc=bcc,
        reply_to=reply_to,
    )
    logger.debug("Message created")

    tempdir = mkdtemp()

    filename = "%s-participants.pdf" % course.number
    filepath = os.path.join(tempdir, filename)
    cp_generator = CourseParticipants({"course": course})
    cp_generator.render_to_pdf(filepath)
    with open(filepath, "rb") as course_participants_pdf:
        email.attach(filename, course_participants_pdf.read(), "application/pdf")
    logger.debug("Participants.pdf attached")
    filename = "mes_cours.pdf"
    filepath = os.path.join(tempdir, filename)
    cp_generator = MyCourses({"instructor": instructor, "courses": Course.objects.filter(instructors=instructor)})
    cp_generator.render_to_pdf(filepath)
    with open(filepath, "rb") as my_courses_pdf:
        email.attach(filename, my_courses_pdf.read(), "application/pdf")
    logger.debug("Courses.pdf attached")

    if not (settings.KEPCHUP_NO_SSF or settings.KEPCHUP_FICHE_SALAIRE_MONTREUX):
        filepath = get_ssf_decompte_heures(course, instructor)
        filename = "SSF_decompte_moniteur_{}_{}.pdf".format(
            instructor.first_name,
            instructor.last_name,
        )
        with open(filepath, "rb") as ssf_decompte_pdf:
            email.attach(filename, ssf_decompte_pdf.read(), "application/pdf")
        logger.debug("Decompte.pdf attached")

    if settings.KEPCHUP_SEND_PRESENCE_LIST:
        filename = "%s-presences.pdf" % course.number
        filepath = os.path.join(tempdir, filename)
        cp_generator = CourseParticipantsPresence({"course": course})
        cp_generator.render_to_pdf(filepath)
        with open(filepath, "rb") as course_participants_presence_pdf:
            email.attach(filename, course_participants_presence_pdf.read(), "application/pdf")
        logger.debug("Presences.pdf attached")

    for additional_doc in settings.KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS:
        filepath = os.path.join(settings.STATIC_ROOT, additional_doc)
        email.attach_file(filepath)

    logger.debug("Email forged, sending...")
    try:
        email.send()
        logger.info(f"Sent instructor email to {instructor.get_email_string()}")
    except SMTPException as smtp_exc:
        logger.error(f"Message {subject} to {[instructor.get_email_string()]} could not be sent: {smtp_exc.message}")
        # 5s for first retry, 25 for second, 2mn for third ~10mn for fourth, 52mn for fifth
        self.retry(countdown=5**self.request.retries)
    finally:
        shutil.rmtree(tempdir)
