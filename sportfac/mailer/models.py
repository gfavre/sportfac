# -*- coding: utf-8 -*-
import re
import os

from django.db import models
from django.utils.html import linebreaks
from django.utils.translation import ugettext as _

from model_utils.models import TimeStampedModel, StatusModel
from model_utils import Choices

from sportfac.models import ListField


__all__ = ('MailArchive', 'Attachment')


class SentMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.sent)


class DraftMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.draft)


class MailArchive(TimeStampedModel, StatusModel):
    STATUS = Choices(('sent', _("sent")),
                     ('draft', _("draft")),)

    subject = models.CharField(max_length=255, verbose_name=_("Subject"))
    recipients = ListField(verbose_name=_("Recipients"))
    bcc_recipients = ListField(verbose_name=_("BCC recipients"), null=True)
    messages = ListField(verbose_name=_("Message"))
    template = models.CharField(max_length=255, verbose_name=_("Template"))

    objects = models.Manager()
    draft = DraftMailManager()
    sent = SentMailManager()

    def admin_recipients(self):
        r = re.compile(r'(?P<name>[\w\s^<]+) <(?P<email>[^>]+)>', re.U)

        def clean_email(name):
            m = r.search(name)
            if m:
                return u'<a href="mailto:{}">{}</a>'.format(m.group('email'), m.group('name'))
            return name

        return u'<br />'.join([clean_email(rec) for rec in self.recipients])
    admin_recipients.allow_tags = True

    def admin_message(self):
        if self.messages:
            return linebreaks(self.messages[0])
        return ''
    admin_message.allow_tags = True


def attachment_path(instance, filename):
    return os.path.join('attachments', str(instance.mail.pk), filename)


class Attachment(TimeStampedModel):
    mail = models.ForeignKey('MailArchive', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=attachment_path)
