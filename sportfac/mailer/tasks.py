from __future__ import absolute_import

from django.core.mail import send_mail as django_send_mail
from django.conf import settings
from celery import shared_task


@shared_task
def send_mail(xsubject, message, from_email, recipients):    
    
    return django_send_mail(subject=subject, 
                            message=message, 
                            from_email=from_email, 
                            recipient_list=[recipient_address,])