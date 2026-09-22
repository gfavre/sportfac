from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from dynamic_preferences.registries import global_preferences_registry

from mailer.pdfutils import PDFRenderer
from sportfac.celery import app

from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent


class DiplomaRenderer(PDFRenderer):
    message_template = "diplomas/certificate.html"
    is_landscape = True
    page_format = "A5"


def render_diplomas(batch, diplomas):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "diplomas.pdf"
        DiplomaRenderer({"batch": batch, "diplomas": diplomas}).render_to_pdf(str(path))
        content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise ValueError("Le service PDF n’a pas retourné un document valide.")
    return content


@app.task
def generate_batch(batch_id, send_after=False):
    if not DiplomaBatch.objects.filter(pk=batch_id, status="queued").update(status="generating"):
        return
    batch = DiplomaBatch.objects.get(pk=batch_id)
    DiplomaEvent.objects.create(batch=batch, action="generation_started")
    try:
        for diploma in batch.diplomas.defer("pdf").all():
            content = render_diplomas(batch, [diploma])
            Diploma.objects.filter(pk=diploma.pk).update(pdf=content)
            DiplomaEvent.objects.create(batch=batch, diploma=diploma, action="generated")
        content = render_diplomas(batch, batch.diplomas.defer("pdf").all())
        DiplomaBatch.objects.filter(pk=batch.pk).update(print_pdf=content, status="ready", error="")
        DiplomaEvent.objects.create(batch=batch, action="generation_completed")
    except Exception as exc:
        DiplomaBatch.objects.filter(pk=batch.pk).update(status="failed", error=str(exc))
        DiplomaEvent.objects.create(batch=batch, action="generation_failed", detail=str(exc))
        raise
    if send_after:
        send_batch(batch_id)


def send_one(diploma, batch, supplements):
    if not Diploma.objects.filter(pk=diploma.pk, mail_status="pending").update(mail_status="sending"):
        return
    recipient = diploma.parent.email
    Diploma.objects.filter(pk=diploma.pk).update(recipient=recipient)
    DiplomaEvent.objects.create(batch=batch, diploma=diploma, action="mail_started", detail=recipient)
    preferences = global_preferences_registry.manager()
    try:
        if not diploma.parent.is_active:
            raise ValueError("Le compte du parent est désactivé.")
        email = EmailMessage(
            batch.subject,
            batch.message,
            preferences["email__FROM_MAIL"] or settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            reply_to=[preferences["email__REPLY_TO_MAIL"]],
        )
        email.attach(f"diplome-{diploma.pk}.pdf", bytes(diploma.pdf), "application/pdf")
        for supplement in supplements:
            email.attach(supplement.name, bytes(supplement.content), "application/pdf")
        if email.send() != 1:
            raise RuntimeError("Le serveur mail n’a pas confirmé l’envoi.")
        Diploma.objects.filter(pk=diploma.pk).update(mail_status="sent", sent_at=timezone.now())
        DiplomaEvent.objects.create(batch=batch, diploma=diploma, action="mail_sent", detail=recipient)
    except Exception as exc:
        # Do not retry automatically: an SMTP failure can follow actual acceptance.
        Diploma.objects.filter(pk=diploma.pk).update(mail_status="failed")
        DiplomaEvent.objects.create(batch=batch, diploma=diploma, action="mail_failed", detail=str(exc))


@app.task
def send_batch(batch_id):
    batch = DiplomaBatch.objects.get(pk=batch_id)
    if batch.status != "ready":
        return
    published = batch.diplomas.filter(published_at__isnull=True, pdf__isnull=False).update(published_at=timezone.now())
    if published:
        DiplomaEvent.objects.create(batch=batch, action="publish")
    supplements = list(batch.supplements.all())
    for diploma in batch.diplomas.filter(
        published_at__isnull=False, pdf__isnull=False, mail_status="pending"
    ).select_related("parent"):
        send_one(diploma, batch, supplements)
