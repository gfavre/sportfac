# -*- coding: utf-8 -*-
import json
import urllib

from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.db.models import Min, Max
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.generic import DetailView, ListView, View

from braces.views import LoginRequiredMixin, UserPassesTestMixin
import requests

from mailer.forms import CourseMailForm, InstructorCopiesForm
from mailer.mixins import ArchivedMailMixin
import mailer.views as mailer_views
from sportfac.views import WizardMixin, NotReachableException
from .models import Activity, Course, PaySlip


__all__ = ('InstructorMixin', 'ActivityDetailView', 'ActivityListView',
           'CustomParticipantsCustomMailView',
           'MyCoursesListView', 'MyCourseDetailView',
           'MailUsersView', 'CustomMailPreview', 'MailCourseInstructorsView',
           'PaySlipDetailView')


class InstructorMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports responsible"""
    pk_url_kwarg = 'course'

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Course, pk=pk)

    def test_func(self, user):
        # noinspection PyUnresolvedReferences
        if self.pk_url_kwarg in self.kwargs:
            course = self.get_object()
            return user.is_active and user.is_instructor_of(course)
        return user.is_active and user.is_instructor


class CourseAccessMixin(UserPassesTestMixin, LoginRequiredMixin):
    pk_url_kwarg = 'course'

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Course, pk=pk)

    def test_func(self, user):
        course = self.get_object()
        return user.is_authenticated() and (user.is_instructor_of(course) or
                                            user in [p.child.family for p in course.participants.all()])


class ActivityDetailView(DetailView):
    model = Activity

    def get_queryset(self):
        prefetched = Activity.objects.prefetch_related('courses', 'courses__participants', 'courses__instructors')
        return prefetched.all()

    def get_context_data(self, **kwargs):
        context = super(ActivityDetailView, self).get_context_data(**kwargs)
        activity = kwargs['object']
        if not self.request.user.is_authenticated():
            context['registrations'] = {}
            return context

        registrations = {}
        children = self.request.user.children.all()
        for course in activity.courses.prefetch_related('participants__child'):
            participants = [reg.child for reg in course.participants.all()]
            for child in children:
                if child in participants:
                    registrations[course] = participants
                    break

        context['registrations'] = registrations
        return context


class ActivityListView(LoginRequiredMixin, WizardMixin, ListView):
    model = Activity

    @staticmethod
    def check_initial_condition(request):
        if not request.user.children.exists():
            raise NotReachableException('No children available')
        from registrations.models import Bill
        if Bill.objects.filter(family=request.user,
                               status=Bill.STATUS.waiting,
                               payment_method=Bill.METHODS.datatrans).exists():
            raise NotReachableException('Payment expected first')

    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        from backend.dynamic_preferences_registry import global_preferences_registry
        context['MAX_REGISTRATIONS'] = global_preferences_registry.manager()['MAX_REGISTRATIONS']
        times = Course.objects.visible().aggregate(Max('end_time'), Min('start_time'))
        start_time = times['start_time__min']
        end_time = times['end_time__max']
        context['START_HOUR'] = start_time and start_time.hour or 8

        if end_time:
            if end_time.minute == 0:
                context['END_HOUR'] = end_time.hour
            else:
                context['END_HOUR'] = (end_time.hour + 1) % 24
        else:
            context['END_HOUR'] = 19
        return context


class MyCoursesListView(InstructorMixin, ListView):
    template_name = 'activities/course_list.html'

    def get_queryset(self):
        return Course.objects.filter(instructors=self.request.user)


class MyCourseDetailView(CourseAccessMixin, DetailView):
    model = Course
    template_name = 'activities/course_detail.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity').\
        prefetch_related('participants__child__school_year', 'participants__child__family', 'instructors')


class MailUsersView(CourseAccessMixin, View):

    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get('data', '[]'))))
        self.request.session['mail-userids'] = userids
        params = ''
        if 'prev' in request.GET:
            params = '?prev=' + urllib.urlencode(request.GET.get('prev'))
        return HttpResponseRedirect(reverse('activities:mail-custom-participants-custom',
                                            kwargs={'course': kwargs['course']}) + params)


class CustomMailCreateView(InstructorMixin, mailer_views.ParticipantsMailCreateView):
    template_name = 'activities/mail-create.html'
    form_class = CourseMailForm

    def get_success_url(self):
        course = self.kwargs['course']
        return reverse('activities:mail-preview', kwargs={'course': course})


class CustomMailPreview(InstructorMixin, ArchivedMailMixin,
                        mailer_views.ParticipantsMailPreviewView):
    group_mails = True
    template_name = 'activities/mail-preview-editlink.html'
    edit_url = reverse_lazy('activities:mail-participants-custom')

    def get_edit_url(self):
        return self.course.get_custom_mail_instructors_url()

    def get_success_url(self):
        return reverse('activities:course-detail', kwargs=self.kwargs)

    def get_reply_to_address(self):
        return self.request.user.get_email_string()


class CustomParticipantsCustomMailView(InstructorMixin, mailer_views.MailCreateView):
    template_name = 'activities/mail-create.html'
    form_class = CourseMailForm

    def get(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.course = get_object_or_404(Course, pk=self.kwargs['course'])
        return super(CustomParticipantsCustomMailView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.course = get_object_or_404(Course, pk=self.kwargs['course'])
        return super(CustomParticipantsCustomMailView, self).post(*args, **kwargs)

    def get_success_url(self):
        return reverse('activities:mail-preview', kwargs={'course': self.course.pk})


class MailCourseInstructorsView(InstructorMixin, mailer_views.MailCourseInstructorsView):
    template_name = 'activities/confirm_send.html'
    form_class = InstructorCopiesForm

    def get_success_url(self):
        return reverse('activities:my-courses')

    def get_recipients(self):
        return [self.request.user]


class PaySlipDetailView(DetailView):
    template_name = 'activities/pay-slip-detail.html'
    model = PaySlip

    def get(self, request, *args, **kwargs):
        if self.request.GET.get('pdf', False):
            return self.pdf()
        return super(PaySlipDetailView, self).get(request, *args, **kwargs)

    def pdf(self):
        """output: filelike object"""
        self.object = self.get_object()
        url = self.request.build_absolute_uri(self.object.get_absolute_url())
        phantomjs_conf = {
            'renderType': 'pdf',
            'omitBackground': True,
            "renderSettings": {
                'emulateMedia': 'print',
                'pdfOptions': {
                    'format': 'A4',
                    'landscape': False,
                    'preferCSSPageSize': True,
                }
            }
        }
        if '127.0.0.1' in url:
            context = self.get_context_data(object=self.object)
            page = render_to_string(self.template_name, context=context, request=self.request)
            phantomjs_conf['content'] = page
        else:
            phantomjs_conf['url'] = url
        pdf = requests.post(
            'https://PhantomJsCloud.com/api/browser/v2/{}/'.format(
                settings.PHANTOMJSCLOUD_APIKEY
            ),
            json.dumps(phantomjs_conf)
        )
        if not pdf.status_code == 200:
            raise IOError(pdf.text)
        response = HttpResponse(pdf.content, content_type="application/pdf")
        response['Content-Disposition'] = 'attachment; filename=%s.pdf' % self.object.pk
        return response
