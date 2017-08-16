# -*- coding: utf-8 -*-
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.template.defaultfilters import urlencode
from django.views.generic import ListView

from mailer.views import (MailView, MailCreateView, CustomMailMixin,
                          MailParticipantsView, MailCourseInstructorsView, MailPreviewView)
from mailer.forms import AdminMailForm, CourseMailForm
from mailer.models import MailArchive
from profiles.models import FamilyUser
from registrations.models import Bill, Registration
from registrations.views import BillMixin
from .mixins import BackendMixin

__all__ = ['MailArchiveListView', 'NeedConfirmationView',
           'NotPaidYetView', 'BackendMailParticipantsView', 
           'MailConfirmationParticipantsView',
           'CustomMailParticipantsCreateView', 'CustomMailParticipantsPreview',
           'CustomUserCustomMailCreateView', 'CustomUserCustomMailPreview',
           'BackendMailCourseInstructorsView', ]


class MailArchiveListView(BackendMixin, ListView):
    queryset = MailArchive.sent.all()
    template_name = 'backend/mail/list.html'


class NeedConfirmationView(BackendMixin, MailView):
    """Mail to people having not confirmed activities yet."""
    success_url = reverse_lazy('backend:home')
    subject_template = 'mailer/need_confirmation_subject.txt'
    message_template = 'mailer/need_confirmation.txt'
    
    def get_recipients_list(self):
        parents = list(set([reg.child.family for reg in Registration.objects.waiting()]))
        return parents
    
    def get_context_data(self, **kwargs):
        context = super(NeedConfirmationView, self).get_context_data(**kwargs)
        context['url'] = ''.join((settings.DEBUG and 'http://' or 'https://',
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context
 

class NotPaidYetView(BackendMixin, BillMixin, MailPreviewView):
    """Mail to people having registered to courses but not paid yet"""
    
    success_url = reverse_lazy('backend:home')
    subject_template = 'mailer/notpaid_subject.txt'
    message_template = 'mailer/notpaid.txt'
    
    def get_recipients_list(self):
        bills = Bill.objects.filter(status=Bill.STATUS.waiting, total__gt=0)
        return FamilyUser.objects.filter(pk__in=[bill.family.pk for bill in bills])


class BackendMailParticipantsView(BackendMixin, MailParticipantsView):
    pass 


class MailConfirmationParticipantsView(BackendMixin, MailParticipantsView):
    subject_template = 'mailer/course_begin_subject.txt'
    message_template = 'mailer/course_begin.txt'


class BackendMailCourseInstructorsView(BackendMixin, MailCourseInstructorsView):
    template_name = 'backend/course/confirm_send.html'

    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)


class CustomMailParticipantsCreateView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'

    def get_success_url(self):
        course = self.kwargs['course']                
        return reverse('backend:mail-participants-custom-preview', 
                       kwargs={'course': course})


class CustomMailParticipantsPreview(CustomMailMixin, BackendMailParticipantsView):
    template_name = 'backend/mail/preview-editlink.html'
    form_class = CourseMailForm

    def get_context_data(self, **kwargs):
        kwargs['prev'] = self.request.GET.get('prev', None)
        return super(CustomMailParticipantsPreview, self).get_context_data(**kwargs)

    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)

    def post(self, request, *args, **kwargs):
        redirect = super(CustomMailParticipantsPreview, self).post(request, *args, **kwargs)
        try:
            del self.request.session['mail']
            del self.request.session['mail-userids']
        except KeyError:
            pass
        return redirect


class CustomUserCustomMailCreateView(BackendMixin, MailCreateView):
    template_name = 'backend/mail/create.html'
    success_url = reverse_lazy('backend:custom-mail-custom-users-preview')
    form_class = AdminMailForm

    def get_success_url(self):
        params = ''
        if 'prev' in self.request.GET:
            params = '?prev=' + urlencode(self.request.GET.get('prev'))
        return self.success_url + params

    def get_context_data(self, **kwargs):
        kwargs['prev'] = self.request.GET.get('prev', None)
        return super(CustomUserCustomMailCreateView, self).get_context_data(**kwargs)


class CustomUserCustomMailPreview(BackendMixin, MailPreviewView):
    success_url = reverse_lazy('backend:user-list')
    template_name = 'backend/mail/preview.html'
    edit_url = reverse_lazy('backend:custom-mail-custom-users')
    #def get_recipients_list(self):
    #    if 'mail-userids' in self.request.session:
    #        return FamilyUser.objects.filter(id__in=self.request.session['mail-userids'])
    #    return []
#
    #def get_context_data(self, **kwargs):
    #    kwargs['cancel_url'] = self.request.GET.get('prev', None)
    #    kwargs['url'] = ''.join((settings.DEBUG and 'http://' or 'https://',
    #                             get_current_site(self.request).domain,
    #                             reverse('wizard_confirm')))
    #    return super(CustomUserCustomMailPreview, self).get_context_data(**kwargs)
#
    #def post(self, request, *args, **kwargs):
    #    redirect = super(CustomUserCustomMailPreview, self).post(request, *args, **kwargs)
    #    del self.request.session['mail']
    #    del self.request.session['mail-userids']
    #    return redirect
