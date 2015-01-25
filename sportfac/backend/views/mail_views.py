from django.contrib import messages
from django.contrib.formtools.wizard.views import SessionWizardView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.models import get_current_site
from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse, reverse_lazy
from django.template import loader, Context, RequestContext
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from profiles.models import FamilyUser, Registration
from mailer.views import MailView, MailCreateView
from mailer.models import MailArchive
from activities.models import Course

from .mixins import BackendMixin

__all__ = ['MailArchiveListView', 'NeedConfirmationView',
           'NotPaidYetView', 'ParticipantsView',
           'CustomMailParticipantsView', 'CustomMailParticipantsPreview']


class MailArchiveListView(BackendMixin, ListView):
    queryset = MailArchive.sent.all()
    template_name = 'backend/mail/list.html'



class NeedConfirmationView(BackendMixin, MailView):
    "Mail to people having not confirmed activities yet."
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet'
    message_template = 'mailer/confirmation.txt'
    
    def get_recipients_list(self):
        parents = list(set([reg.child.family for reg in  Registration.objects.waiting()]))
        return parents
    
    def get_context_data(self, **kwargs):
        context = super(NeedConfirmationView, self).get_context_data(**kwargs)
        context['url'] = ''.join(('http://', 
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context
 

class NotPaidYetView(BackendMixin, MailView):
    "Mail to people having registered to courses but not paid yet"
    recipients_queryset = FamilyUser.objects.filter(finished_registration=True, 
                                                    paid=False, total__gt=0)
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet - rappel'
    message_template = 'mailer/notpaid.txt'


class ParticipantsView(BackendMixin, MailView):
    recipients_queryset = FamilyUser.objects.filter(is_superuser=False)
    success_url = reverse_lazy('backend:home')
    subject = 'Inscription au sport scolaire facultatif - EP Coppet'
    message_template = 'mailer/course-begin.txt'

    def get_recipient_address(self, recipient):
       return super(ParticipantsView, self).get_recipient_address(recipient.child.family)
    
    def add_recipient_context(self, recipient, context):
        context['recipient'] = recipient.child.family
        context['child'] = recipient.child
        context['registration'] = recipient
   
    def add_mail_context(self, mailnumber, context):
        "Get context, add navigation"
        context['to_email'] = self.get_recipient_address(context['registration'] )
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)        

    
    def get_recipients_list(self):
        return self.course.participants.all()
    
    def get_context_data(self, **kwargs):
        context = super(ParticipantsView, self).get_context_data(**kwargs)
        try:
            course = Course.objects.get(number=self.kwargs.get('course'))
            self.course = course
            context['course'] = course
        except Course.DoesNotExist:
            raise Http404(_("No course found"))

        context['url'] = ''.join(('http://', 
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context


class CustomMailParticipantsView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'
    
    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('backend:mail-participants-custom-preview', 
                       kwargs={'course': course })
    
     

class CustomMailParticipantsPreview(ParticipantsView):
    template_name = 'backend/mail/preview-editlink.html'
    
    def get_subject(self):
        mail_id = self.request.session.get('mail', None)
        try:
            mail = MailArchive.objects.get(id=mail_id)
        except MailArchive.DoesNotExist:
            raise Http404()
        return mail.subject
    
    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)
        
        
    def get_message_template(self):
        mail_id = self.request.session.get('mail', None)
        try:
            mail = MailArchive.objects.get(id=mail_id)
        except MailArchive.DoesNotExist:
            raise Http404()
        return self.resolve_template(mail.template)
    
    def post(self, request, *args, **kwargs):
        redirect = super(CustomMailParticipantsPreview, self).post(request, *args, **kwargs)
        del self.request.session['mail']
        return redirect 


#class ParticipantsView(ParticipantsBeginView):
    



class TestSuperadmin(BackendMixin, MailView):
    "Mail to people having registered to courses but not paid yet"
    recipients_queryset = FamilyUser.objects.filter(is_superuser=True)
    success_url = reverse_lazy('backend:home')
    subject = 'Test superadmin'
    message_template = 'mailer/notpaid.txt'
 