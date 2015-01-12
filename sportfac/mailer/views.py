import six

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import loader, Context, RequestContext
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, ContextMixin


# Create your views here.
class MailMixin(ContextMixin):
    recipients_queryset = None
    success_url = None
    from_email = None
    subject = None
    message_template = None
    from_address = None
    success_message = ''
    
    def get_recipients_list(self):
        if self.recipients_queryset is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'recipients_queryset' or an implementation of 'get_subject_template'")
        else:
            return self.recipients_queryset.all()

        if self.recipients_queryset:
            return self.recipients_queryset.all()
        return []
    
    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url
    
    def get_recipient_address(self, recipient):
        to = '%s %s <%s>' 
        return to % (recipient.first_name, recipient.last_name, recipient.email)
    
    def resolve_template(self, template):
        "Accepts a template object, path-to-template or list of paths"
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, six.string_types):
            return loader.get_template(template)
        else:
            return template
    
    #def get_context_data(self, **kwargs):
    #    context = super(MailMixin, self).get_context_data(**kwargs)
    #    recipients = self.get_recipients_list()
    #    context['recipients'] = recipients
    #    context['recipients_emails'] = [self.get_recipient_address(rcp) for rcp in recipients]
    
        
    def get_subject(self):
        if self.subject is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'subject' or an implementation of 'get_subject'")
        return self.subject 

    def get_message_template(self):
        if self.message_template is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'message_template' or an implementation of 'get_subject_template'")
        else:
            return self.resolve_template(self.message_template)
    
    def get_from_address(self):
        if self.from_address:
            return self.from_address
        return settings.DEFAULT_FROM_EMAIL
    
    def get_success_message(self):
        if self.success_message:
            return self.success_message
        return _("Message has been scheduled to be sent.")
    
    def mail(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        recipients = self.get_recipients_list()
        
        for recipient in recipients:
            context = self.get_context_data(**kwargs)
            context['mailer_recipient'] = recipient
            context = Context(context)
            to_email = self.get_recipient_address(recipient)
            subject = self.get_subject()
            message = self.get_message_template().render(context)
            from_email = self.get_from_address()
            send_mail(subject=subject, message=message, 
                      from_email=from_email, 
                      recipient_list=[to_email,])
        messages.add_message(self.request, messages.SUCCESS, 
                             self.get_success_message())
        return HttpResponseRedirect(success_url)
   
    def post(self, request, *args, **kwargs):
        return self.mail(request, *args, **kwargs)
          
   


class MailView(MailMixin, TemplateView):
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    
