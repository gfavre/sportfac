import six, time, itertools

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import loader, Context, RequestContext
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, ContextMixin
from django.views.generic.edit import FormView
from django.http import Http404


from constance import config
from dbtemplates.models import Template

from .models import MailArchive
from .tasks import send_mail
from .forms import MailForm

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
        return config.FROM_MAIL
    
    def get_success_message(self):
        if self.success_message:
            return self.success_message
        return _("Message has been scheduled to be sent.")
    
    def get_mail_body(self, context):
        return self.get_message_template().render(Context(context))    
    
    def add_recipient_context(self, recipient, context):
        context['recipient'] = recipient
    
    def mail(self, request, *args, **kwargs):
        base_context = self.get_context_data(**kwargs)
        recipients = self.get_recipients_list()
        emails = []
        recipients_addresses = []
        subject = self.get_subject()
        from_email = self.get_from_address()
        for recipient in recipients:
            context = base_context.copy()
            self.add_recipient_context(recipient, context)
            message = self.get_mail_body(context)
            recipient_address = self.get_recipient_address(recipient)
            send_mail.delay(subject=subject, 
                            message=message, 
                            from_email=from_email, 
                            recipients=[recipient_address,])
            emails.append(message)
            recipients_addresses.append(recipient_address)
        MailArchive.objects.create(subject=subject, messages=emails, 
                                   recipients=recipients_addresses,
                                   template=self.message_template)
        messages.add_message(self.request, messages.SUCCESS, 
                             self.get_success_message())
        
        
   
    def post(self, request, *args, **kwargs):
        self.mail(request, *args, **kwargs)
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url) 


class MailView(MailMixin, TemplateView):
    template_name = 'backend/mail/preview.html'
    
    def get_context_data(self, **kwargs):
        context = super(MailView, self).get_context_data(**kwargs)
        context['signature'] = config.SIGNATURE
        current_site = get_current_site(self.request)
        context['site_name'] = current_site.name
        context['site_url'] = 'http://%s' % current_site.domain
        return context
        
    def add_navigation_context(self, mailnumber, mails, context):
        context['total'] = len(mails)
        context['mailidentifier'] = mailnumber + 1
        context['has_prev'] = mailnumber != 0
        context['prev'] = mailnumber
        context['has_next'] = mailnumber +1 != context['total']
        context['next'] = mailnumber + 2
    
    def add_mail_context(self, mailnumber, context):
        "Get context, add navigation"
        context['to_email'] = self.get_recipient_address(context['recipient'] )
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)        
 
    def get(self, request, *args, **kwargs):
        "Preview emails."
        mailnumber = int(self.request.GET.get('number', 1)) - 1
        
        context = self.get_context_data(**kwargs)
        
        recipients = self.get_recipients_list()
        self.add_navigation_context(mailnumber, recipients, context)
        self.add_recipient_context(recipients[mailnumber], context)
        self.add_mail_context(mailnumber, context)
        
        return self.render_to_response(context)


class MailCreateView(FormView):
    form_class = MailForm            
    
    def get_archive_from_session(self):
        if not 'mail' in self.request.session:
            return None
        try:
            return MailArchive.objects.get(id=self.request.session['mail'])
        except MailArchive.DoesNotExist:
            del self.request.session['mail']
            return None
    
    def get_template_from_archive(self, archive):
        template, created = Template.objects.get_or_create(name=archive.template)
        return template
    
    def get_initial(self):
        if not 'mail' in self.request.session:
            return {}
        archive = MailArchive.objects.get(id=self.request.session['mail'])
        template = Template.objects.get(name=archive.template)
        return {'message': template.content,
                'subject': archive.subject}
    
    def form_valid(self, form):
        archive = self.get_archive_from_session()
        if archive:
            template = self.get_template_from_archive(archive)
            archive.subject = form.cleaned_data['subject']
            archive.save()
        else:
            template = Template()
            orig = time.strftime('%Y-%m-%d-%H-%M-custom')
            template.name = orig + '.txt'
            for x in itertools.count(1):
                if not Template.objects.filter(name=template.name).exists():
                    break
                template.name = '%s-%d.txt' % (orig, x)
            archive = MailArchive.objects.create(status=MailArchive.STATUS.draft,
                                                 subject=form.cleaned_data['subject'],
                                                 recipients=[],
                                                 messages=[],
                                                 template=template.name)
            self.request.session['mail'] = archive.id
            
        template.content = form.cleaned_data['message']
        template.save()
               
        return super(MailCreateView, self).form_valid(form)