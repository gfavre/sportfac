import re
from django.db import models
from django.utils.html import linebreaks

from model_utils.models import TimeStampedModel, StatusModel
from model_utils import Choices

from sportfac.models import ListField

__all__ = ('MailArchive', )

class SentMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.sent)

class DraftMailManager(models.Manager):
    def get_queryset(self):
        return super(SentMailManager, self).get_queryset().filter(status=MailArchive.STATUS.draft)
    


class MailArchive(TimeStampedModel, StatusModel):
    STATUS = Choices('sent', 'draft')

    subject = models.CharField(max_length=255)
    recipients = ListField()
    messages = ListField()
    template = models.CharField(max_length=255)
    
    objects = models.Manager()
    draft = DraftMailManager()
    sent = SentMailManager()
    
    def admin_recipients(self):
        r = re.compile('(?P<name>[\w\s^\<]+) \<(?P<email>[^\>]+)\>')
        def clean_email(name):
            m = r.search(name)
            return '<a href="mailto:%s">%s</a>' % (m.group('email'), m.group('name'))
        
        return '<br />'.join([clean_email(rec) for rec in self.recipients])
    admin_recipients.allow_tags = True
    
    def admin_message(self):
        if self.messages:
            return linebreaks(self.messages[0])
        return ''
    admin_message.allow_tags = True
