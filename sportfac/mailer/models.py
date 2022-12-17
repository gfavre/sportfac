# -*- coding: utf-8 -*-
import os
import re

from django.db import models
from django.urls import reverse
from django.utils.html import linebreaks
from django.utils.translation import gettext as _

from ckeditor.fields import RichTextField
from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel

from sportfac.models import ListField


__all__ = ("MailArchive", "Attachment", "GenericEmail")


class SentMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.sent)


class DraftMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.draft)


class MailArchive(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ("sent", _("sent")),
        ("draft", _("draft")),
    )

    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    recipients = ListField(verbose_name=_("Recipients"))
    bcc_recipients = ListField(verbose_name=_("BCC recipients"), null=True)
    messages = ListField(verbose_name=_("Message"))
    template = models.CharField(max_length=255, verbose_name=_("Template"))

    objects = models.Manager()
    draft = DraftMailManager()
    sent = SentMailManager()

    def admin_recipients(self):
        r = re.compile(r"(?P<name>[\w\s^<]+) <(?P<email>[^>]+)>", re.U)

        def clean_email(name):
            m = r.search(name)
            if m:
                return '<a href="mailto:{}">{}</a>'.format(m.group("email"), m.group("name"))
            return name

        return "<br />".join([clean_email(rec) for rec in self.recipients])

    admin_recipients.allow_tags = True

    def admin_message(self):
        if self.messages:
            return linebreaks(self.messages[0])
        return ""

    admin_message.allow_tags = True


def attachment_path(instance, filename):
    return os.path.join("attachments", str(instance.mail.pk), filename)


class Attachment(TimeStampedModel):
    mail = models.ForeignKey("MailArchive", on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=attachment_path)


class GenericEmail(TimeStampedModel):
    subject = models.CharField(blank=True, max_length=100)
    subject_template = models.ForeignKey(
        "dbtemplates.Template", related_name="email_subject", on_delete=models.CASCADE
    )
    body_template = models.ForeignKey(
        "dbtemplates.Template", related_name="email_body", on_delete=models.CASCADE
    )
    help_text = RichTextField(blank=True)

    @property
    def best_subject(self):
        return self.subject or self.subject_template.content

    def get_absolute_url(self):
        return reverse("backend:emails-update", kwargs={"pk": self.pk})
