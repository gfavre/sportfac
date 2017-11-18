# -*- coding: utf-8 -*-
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.views.generic import ListView

import mailer.views as mailer_views
from mailer.forms import AdminMailForm
from mailer.models import MailArchive
from profiles.models import FamilyUser
from registrations.models import Bill, Registration
from registrations.views import BillMixin
from .mixins import BackendMixin

__all__ = ['MailArchiveListView', 'NeedConfirmationView',
           'NotPaidYetView',
           'MailConfirmationParticipantsView',

           'MailCreateView', 'MailPreview',
           'ParticipantsMailCreateView', 'ParticipantsMailPreview',
           'MailCourseInstructorsView', ]


class MailArchiveListView(BackendMixin, ListView):
    queryset = MailArchive.sent.all()
    template_name = 'backend/mail/list.html'


class MailCreateView(BackendMixin, mailer_views.MailCreateView):
    """Send email to a given set of users - form"""
    template_name = 'backend/mail/create.html'
    success_url = reverse_lazy('backend:custom-mail-custom-users-preview')
    form_class = AdminMailForm


class MailPreview(BackendMixin, mailer_views.ArchivedMailMixin,
                  mailer_views.MailPreviewView):
    """Send email to a given set of users - preview"""
    success_url = reverse_lazy('backend:user-list')
    template_name = 'backend/mail/preview.html'
    edit_url = reverse_lazy('backend:custom-mail-custom-users')

    def get_cancel_url(self):
        return self.request.GET.get('prev', None)

    def get_context_data(self, **kwargs):
        kwargs['url'] = ''.join((settings.DEBUG and 'http://' or 'https://',
                                 get_current_site(self.request).domain,
                                 reverse('wizard_confirm')))
        return super(MailPreview, self).get_context_data(**kwargs)


class ParticipantsMailCreateView(BackendMixin, mailer_views.ParticipantsMailCreateView):
    """Send email to all participants of a course - form"""
    template_name = 'backend/mail/create.html'

    def get_success_url(self):
        return reverse('backend:mail-participants-custom-preview', kwargs={'course': self.course.pk})


class ParticipantsMailPreview(BackendMixin,
                              mailer_views.ArchivedMailMixin,
                              mailer_views.ParticipantsMailPreviewView):
    """Send email to all participants of a course - preview"""
    template_name = 'backend/mail/preview.html'
    group_mails = True

    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)


class MailCourseInstructorsView(BackendMixin, mailer_views.MailCourseInstructorsView):
    template_name = 'backend/course/confirm_send.html'

    def get_success_url(self):
        return reverse('backend:course-detail', kwargs=self.kwargs)


class MailConfirmationParticipantsView(BackendMixin,
                                       mailer_views.ParticipantsMixin,
                                       mailer_views.TemplatedEmailMixin,
                                       mailer_views.BrowsableMailPreviewView):
    subject_template = 'mailer/course_begin_subject.txt'
    message_template = 'mailer/course_begin.txt'
    template_name = 'backend/mail/preview-browse.html'
    edit_url = None
    group_mails = False

    def get_success_url(self):
        return self.course.backend_url

    def get_cancel_url(self):
        return self.course.backend_url


class NotPaidYetView(BackendMixin,
                     BillMixin,
                     mailer_views.TemplatedEmailMixin,
                     mailer_views.BrowsableMailPreviewView):
    """Mail to people having registered to courses but not paid yet"""

    subject_template = 'mailer/notpaid_subject.txt'
    message_template = 'mailer/notpaid.txt'
    template_name = 'backend/mail/preview-browse.html'
    success_url = reverse_lazy('backend:home')

    def get_context_data(self, **kwargs):
        kwargs['delay'] = self.global_preferences['payment__DELAY_DAYS']
        kwargs['iban'] = self.global_preferences['payment__IBAN']
        kwargs['address'] = self.global_preferences['payment__ADDRESS']
        kwargs['place'] = self.global_preferences['payment__PLACE']
        return super(NotPaidYetView, self).get_context_data(**kwargs)

    def get_recipients(self):
        bills = Bill.objects.filter(status=Bill.STATUS.waiting, total__gt=0)
        return list(FamilyUser.objects.filter(pk__in=[bill.family.pk for bill in bills]))


class NeedConfirmationView(BackendMixin, mailer_views.TemplatedEmailMixin, mailer_views.BrowsableMailPreviewView):
    """Mail to people having not confirmed activities yet."""
    success_url = reverse_lazy('backend:home')
    subject_template = 'mailer/need_confirmation_subject.txt'
    message_template = 'mailer/need_confirmation.txt'
    template_name = 'backend/mail/preview-browse.html'

    def get_recipients(self):
        parents = list(set([reg.child.family for reg in Registration.objects.waiting()]))
        return parents

    def get_context_data(self, **kwargs):
        kwargs['url'] = ''.join((settings.DEBUG and 'http://' or 'https://',
                                 get_current_site(self.request).domain,
                                 reverse('wizard_confirm')))
        return super(NeedConfirmationView, self).get_context_data(**kwargs)
