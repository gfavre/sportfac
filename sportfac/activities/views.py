# -*- coding: utf-8 -*-
import json
import urllib

from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Min, Max
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, ListView, View

from braces.views import GroupRequiredMixin, LoginRequiredMixin

from backend import INSTRUCTORS_GROUP
import mailer.views as mailer_views
from mailer.forms import CourseMailForm, InstructorCopiesForm
from mailer.mixins import ArchivedMailMixin
from sportfac.views import WizardMixin
from .models import Activity, Course


__all__ = ('InstructorMixin', 'ActivityDetailView', 'ActivityListView',
           'CustomParticipantsCustomMailView',
           'MyCoursesListView', 'MyCourseDetailView',
           'MailUsersView', 'CustomMailPreview', 'MailCourseInstructorsView')


class InstructorMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member
       of sports responisbles group."""
    group_required = INSTRUCTORS_GROUP


class CourseAccessMixin(InstructorMixin):
    pk_url_kwarg = 'course'

    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Course, pk=pk)

    def check_membership(self, group):
        if not super(CourseAccessMixin, self).check_membership(group):
            return self.request.user in [p.child.family for p in self.get_object().participants.all()]
        return True


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
        self.course = get_object_or_404(Course, pk=self.kwargs['course'])
        return super(CustomParticipantsCustomMailView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
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
