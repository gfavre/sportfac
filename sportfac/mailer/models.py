import re
from django.db import models
from django.utils.html import linebreaks

from model_utils.models import TimeStampedModel

from sportfac.models import ListField

# Create your models here.
class MailArchive(TimeStampedModel):
    subject = models.CharField(max_length=255)
    recipients = ListField()
    messages = ListField()
    template = models.CharField(max_length=255)
    
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
