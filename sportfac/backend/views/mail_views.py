from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sites.models import get_current_site
from django.http import Http404
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse, reverse_lazy
from django.template import loader, Context, RequestContext
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView, View

from profiles.models import FamilyUser, Registration
from mailer.views import MailView, MailCreateView, CustomMailMixin, MailParticipantsView
from mailer.models import MailArchive
from activities.models import Course

from .mixins import BackendMixin

__all__ = ['MailArchiveListView', 'NeedConfirmationView',
           'NotPaidYetView', 'ParticipantsView',
           'CustomMailParticipantsCreateView', 'CustomMailParticipantsPreview',
           'CustomUserCustomMailCreateView', 'CustomUserCustomMailPreview',]


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
    
    
class ParticipantsView(BackendMixin, MailParticipantsView):
    pass 



    


class CustomMailParticipantsCreateView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'
    
    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('backend:mail-participants-custom-preview', 
                       kwargs={'course': course })
          
class CustomMailParticipantsPreview(CustomMailMixin, ParticipantsView):
    template_name = 'backend/mail/preview-editlink.html'
        
    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)
        
    def post(self, request, *args, **kwargs):
        redirect = super(CustomMailParticipantsPreview, self).post(request, *args, **kwargs)
        del self.request.session['mail']
        return redirect 

    


class CustomUserCustomMailCreateView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'
    success_url = reverse_lazy('backend:custom-mail-custom-users-preview')
        
    
class CustomUserCustomMailPreview(BackendMixin, CustomMailMixin, MailView):
    success_url = reverse_lazy('backend:user-list')
    
    def get_recipients_list(self):
        return FamilyUser.objects.filter(id__in=self.request.session['mail-userids'])
    
    def get_context_data(self, **kwargs):
        context = super(CustomUserCustomMailPreview, self).get_context_data(**kwargs)
        context['url'] = ''.join(('http://', 
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context
    
    def post(self, request, *args, **kwargs):
        redirect = super(CustomUserCustomMailPreview, self).post(request, *args, **kwargs)
        del self.request.session['mail']
        del self.request.session['mail-userids']
        return redirect






class TestSuperadmin(BackendMixin, MailView):
    "Mail to people having registered to courses but not paid yet"
    recipients_queryset = FamilyUser.objects.filter(is_superuser=True)
    success_url = reverse_lazy('backend:home')
    subject = 'Test superadmin'
    message_template = 'mailer/notpaid.txt'
 