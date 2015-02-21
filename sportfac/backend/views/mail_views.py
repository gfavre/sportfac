from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import ListView

from mailer.views import (MailView, MailCreateView, CustomMailMixin,
                          MailParticipantsView, MailCourseResponsibleView)
from mailer.models import MailArchive
from profiles.models import FamilyUser, Registration
from .mixins import BackendMixin

__all__ = ['MailArchiveListView', 'NeedConfirmationView',
           'NotPaidYetView', 'BackendMailParticipantsView', 
           'MailConfirmationParticipantsView',
           'CustomMailParticipantsCreateView', 'CustomMailParticipantsPreview',
           'CustomUserCustomMailCreateView', 'CustomUserCustomMailPreview',
           'BackendMailCourseResponsibleView', ]


class MailArchiveListView(BackendMixin, ListView):
    queryset = MailArchive.sent.all()
    template_name = 'backend/mail/list.html'


class NeedConfirmationView(BackendMixin, MailView):
    "Mail to people having not confirmed activities yet."
    success_url = reverse_lazy('backend:home')
    subject_template = 'mailer/need_confirmation_subject.txt'
    message_template = 'mailer/need_confirmation.txt'
    
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
    subject_template = 'mailer/notpaid_subject.txt'
    message_template = 'mailer/notpaid.txt'


class BackendMailParticipantsView(BackendMixin, MailParticipantsView):
    pass 


class MailConfirmationParticipantsView(BackendMixin, MailParticipantsView):
    subject_template = 'mailer/course_begin_subject.txt'
    message_template = 'mailer/course_begin.txt'
    


class BackendMailCourseResponsibleView(BackendMixin, MailCourseResponsibleView):
    template_name = 'backend/course/confirm_send.html'

    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)


class CustomMailParticipantsCreateView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'

    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('backend:mail-participants-custom-preview', 
                       kwargs={'course': course })


class CustomMailParticipantsPreview(CustomMailMixin, BackendMailParticipantsView):
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
