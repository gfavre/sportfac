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
    
    def get_mail_body(self, context):
        return self.get_message_template().render(Context(context))    
    
    def mail(self, request, *args, **kwargs):
        success_url = self.get_success_url()
        recipients = self.get_recipients_list()
        
        for recipient in recipients:
            context = self.get_context_data(**kwargs)
            context.update(get_mail_context(recipient))
            send_mail(subject=self.get_subject(), 
                      message=self.get_mail_body(context), 
                      from_email=self.get_from_address(), 
                      recipient_list=[self.get_recipient_address(recipient),])
        messages.add_message(self.request, messages.SUCCESS, 
                             self.get_success_message())
        return HttpResponseRedirect(success_url)
   
    def post(self, request, *args, **kwargs):
        return self.mail(request, *args, **kwargs)
          
    


class MailView(MailMixin, TemplateView):
    template_name = 'backend/mail/preview.html'
    
    def add_mail_context(self, mailnumber, context):
        "Get context, add navigation"
        
        recipients = self.get_recipients_list()
        context['total'] = recipients.count()
        context['recipient'] = recipients[mailnumber]

        context['to_email'] = self.get_recipient_address(context['recipient'] )
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)
        
        context['mailidentifier'] = mailnumber + 1
        context['has_prev'] = mailnumber != 0
        context['prev'] = mailnumber
        context['has_next'] = mailnumber +1 != context['total']
        context['next'] = mailnumber + 2
        
        return context
 
    def get(self, request, *args, **kwargs):
        "Preview emails."
        mailnumber = int(self.request.GET.get('number', 1)) - 1

        context = self.get_context_data(**kwargs)
        context = self.add_mail_context(mailnumber, context)
        
        return self.render_to_response(context)

    
