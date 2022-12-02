# -*- coding: utf-8 -*-
from __future__ import absolute_import
import collections
import os
from tempfile import mkdtemp

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View
from django.views.generic.detail import SingleObjectMixin

from absences.models import Absence, Session
from absences.utils import closest_session
from activities.models import Course, Activity, ExtraNeed, CoursesInstructors, PaySlip, RATE_MODES
from activities.forms import CourseForm, ExplicitDatesCourseForm, PaySlipForm
from profiles.models import FamilyUser
from registrations.models import ChildActivityLevel, ExtraInfo
from registrations.resources import RegistrationResource
from sportfac.views import CSVMixin
from .mixins import BackendMixin, ExcelResponseMixin
from ..forms import SessionForm
from ..utils import AbsencePDFRenderer, AbsencesPDFRenderer
from six.moves import range

__all__ = ('CourseCreateView', 'CourseDeleteView', 'CourseDetailView',
           'CourseJSCSVView', 'CourseParticipantsExportView',
           'CourseAbsenceView', 'CoursesAbsenceView',
           'CourseListView', 'CourseUpdateView', 'CourseParticipantsView',
           'PaySlipMontreux')


class CourseCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    template_name = 'backend/course/create.html'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been created.')

    def get_context_data(self, **kwargs):
        context = super(CourseCreateView, self).get_context_data(**kwargs)
        context['extra_needs'] = ExtraNeed.objects.all()
        return context

    def get_form_class(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            return ExplicitDatesCourseForm
        return CourseForm

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})

    def get_initial(self):
        initial = super(CourseCreateView, self).get_initial()
        activity = self.request.GET.get('activity', None)
        if activity:
            activity_obj = get_object_or_404(Activity, pk=activity)
            initial['activity'] = activity_obj

        if self.request.GET.get('source'):
            try:
                source = Course.objects.get(pk=self.request.GET.get('source'))
                initial.update(model_to_dict(source))
                del initial['number']
                initial['uptodate'] = False
            except Course.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        self.object = form.save()
        for extra in form.cleaned_data['extra']:
            self.object.extra.add(extra)
        return HttpResponseRedirect(self.get_success_url())


class CourseDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
    success_url = reverse_lazy('backend:course-list')
    success_message = _("Course has been deleted.")
    pk_url_kwarg = 'course'

    def delete(self, request, *args, **kwargs):
        identifier = self.get_object().short_name
        messages.success(self.request,
                         _("Course %(identifier)s has been deleted.") % {
                             'identifier': identifier })
        return super(CourseDeleteView, self).delete(request, *args, **kwargs)


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity') \
        .prefetch_related('participants__child__school_year',
                          'participants__child__family',
                          'participants__child__school',
                          'participants__extra_infos',
                          'instructors',
                          'extra')

    def get_context_data(self, **kwargs):
        context = super(CourseDetailView, self).get_context_data(**kwargs)
        registrations = self.get_object().participants.all()
        context['registrations'] = registrations
        return context


class CourseUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Course
    template_name = 'backend/course/update.html'
    pk_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')

    def get_context_data(self, **kwargs):
        context = super(CourseUpdateView, self).get_context_data(**kwargs)
        context['extra_needs'] = ExtraNeed.objects.all()
        return context

    def get_form_class(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            return ExplicitDatesCourseForm
        return CourseForm

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})

    def get_initial(self):
        initial = super(CourseUpdateView, self).get_initial()
        initial['extra'] = self.get_object().extra.all()
        return initial

    def form_valid(self, form):
        course = self.get_object()
        response = super(CourseUpdateView, self).form_valid(form)
        removed_extras = set(course.extra.all()) - set(form.cleaned_data['extra'])
        for removed_extra in removed_extras:
            course.extra.remove(removed_extra)
        for extra in form.cleaned_data['extra']:
            course.extra.add(extra)
        return response


class CourseAbsenceView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/absences.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.prefetch_related('sessions', 'sessions__absences', 'participants__child',
                                               'instructors') \
        .select_related('activity', )

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            if self.request.user in course.instructors.all():
                instructor = self.request.user
            else:
                instructor = None
            with transaction.atomic():
                session, created = Session.objects.get_or_create(course=course, date=form.cleaned_data['date'],
                                                                 defaults={
                                                                     'instructor': instructor,
                                                                     'activity': course.activity
                                                                 })
                session.fill_absences()
                if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                    session.update_courses_dates()
                if created:
                    messages.success(self.request,
                                     _("Session %s has been added.") % session.date.strftime('%d.%m.%Y'))

        return HttpResponseRedirect(course.get_backend_absences_url())

    def get_context_data(self, **kwargs):
        qs = Absence.objects.select_related('child', 'session').filter(session__course=self.object)
        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by('child__bib_number', 'child__last_name', 'child__first_name')
        else:
            qs = qs.order_by('child__last_name', 'child__first_name')
        sessions = self.object.sessions.all()
        kwargs['sessions'] = dict([(session.date, session) for session in sessions])
        kwargs['closest_session'] = closest_session(sessions)

        # kwargs['sessions'] = dict([(absence.session.date, absence.session) for absence in qs])
        kwargs['all_dates'] = sorted([session_date for session_date in kwargs['sessions'].keys()],
                                     reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC)

        registrations = dict([(registration.child, registration) for registration in self.object.participants.all()])
        child_absences = collections.OrderedDict()
        for (child, registration) in sorted(list(registrations.items()), key=lambda x: x[0].ordering_name):
            child_absences[(child, registration)] = {}
        for absence in qs:
            child = absence.child
            if not child in registrations:
                # happens if child was previously attending this course but is no longer
                continue
            registration = registrations[child]

            the_tuple = (child, registration)
            if the_tuple in child_absences:
                child_absences[the_tuple][absence.session.date] = absence
            else:
                child_absences[the_tuple] = {absence.session.date: absence}
        kwargs['session_form'] = SessionForm()
        kwargs['child_absences'] = child_absences
        kwargs['courses_list'] = Course.objects.select_related('activity')
        if settings.KEPCHUP_REGISTRATION_LEVELS:
            kwargs['levels'] = ChildActivityLevel.LEVELS
            kwargs['child_levels'] = dict(
                [(lvl.child, lvl) for lvl in ChildActivityLevel.objects.filter(activity=self.object.activity)
                    .select_related('child')]
            )
            try:
                questions = ExtraNeed.objects.filter(question_label__startswith=u'Niveau')
                all_extras = dict(
                    [(extra.registration.child, extra.value) for extra in
                     ExtraInfo.objects.filter(registration__course=self.object, key__in=questions)
                         .select_related('registration__child')]
                )
            except ExtraNeed.DoesNotExist:
                all_extras = {}
            kwargs['extras'] = all_extras
        return super(CourseAbsenceView, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        if 'pdf' in self.request.GET:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            renderer = AbsencePDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = u'absences-{}.pdf'.format(slugify(self.object.number))
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type='application/pdf')
            response['Content-Disposition'] = u'attachment; filename="{}"'.format(filename)
            return response
        return super(CourseAbsenceView, self).get(request, *args, **kwargs)


class CoursesAbsenceView(BackendMixin, ListView):
    model = Course
    template_name = 'backend/course/multiple-absences.html'

    def get_queryset(self):
        courses_pk = [int(pk) for pk in self.request.GET.getlist('c') if pk.isdigit()]
        return Course.objects.filter(pk__in=courses_pk)

    def get_context_data(self, **kwargs):
        qs = Absence.objects.filter(session__course__in=self.get_queryset()) \
            .select_related('session', 'child', 'session__course', 'session__course__activity')
        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by('child__bib_number', 'child__last_name', 'child__first_name')
        else:
            qs = qs.order_by('child__last_name', 'child__first_name')
        sessions = Session.objects.filter(course__in=self.get_queryset())
        kwargs['all_dates'] = list(set(sessions.values_list('date', flat=True)))
        kwargs['all_dates'].sort(reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC)
        kwargs['closest_session'] = closest_session(sessions)
        if settings.KEPCHUP_REGISTRATION_LEVELS:
            extras = ExtraInfo.objects.select_related('registration', 'key') \
                .filter(registration__course__in=self.get_queryset(),
                        key__question_label='Niveau de ski/snowboard')
            child_announced_levels = {extra.registration.child: extra.value for extra in extras}
            levels = ChildActivityLevel.objects.select_related('child') \
                .filter(activity__in=set([absence.session.course.activity for
                                          absence in qs]))
            child_levels = {level.child: level for level in levels}

        course_children = dict(
            [(course, [reg.child for reg in course.participants.all()]) for course in self.get_queryset()])
        course_absences = collections.OrderedDict()

        for absence in qs:
            if settings.KEPCHUP_REGISTRATION_LEVELS:
                absence.child.announced_level = child_announced_levels.get(absence.child, '')
                absence.child.level = child_levels.get(absence.child, '')
            if absence.child not in course_children[absence.session.course]:
                continue
            the_tuple = (absence.child, absence.session.course)
            if the_tuple in course_absences:
                course_absences[the_tuple][absence.session.date] = absence
            else:
                course_absences[the_tuple] = {absence.session.date: absence}
        kwargs['course_absences'] = course_absences
        kwargs['levels'] = ChildActivityLevel.LEVELS
        kwargs['session_form'] = SessionForm()

        return super(CoursesAbsenceView, self).get_context_data(**kwargs)

    def post(self, *args, **kwargs):
        pks = self.request.GET.getlist('c')
        courses = Course.objects.filter(pk__in=pks)
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            for course in courses:
                session, created = Session.objects.get_or_create(course=course, activity=course.activity,
                                                                 date=form.cleaned_data['date'])
                if not created:
                    continue
                session.fill_absences()
                if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                    session.update_courses_dates()
                if created:
                    messages.success(self.request, _("Session %s has been added.") % session.date.strftime('%d.%m.%Y'))
        params = '&'.join(['c={}'.format(course.id) for course in courses])
        return HttpResponseRedirect(reverse('backend:courses-absence') + '?' + params)

    def get(self, request, *args, **kwargs):
        if 'pdf' in self.request.GET:
            self.object_list = self.get_queryset()
            context = self.get_context_data()
            renderer = AbsencesPDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = u'absences-{}.pdf'.format('-'.join([slugify(nb) for nb in
                                                           self.object_list.values_list('number', flat=True)]))
            if len(filename) > 100:
                filename = u'absences.pdf'
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type='application/pdf')
            response['Content-Disposition'] = u'attachment; filename="{}"'.format(filename)
            return response
        return super(CoursesAbsenceView, self).get(request, *args, **kwargs)


class CourseJSCSVView(CSVMixin, CourseDetailView):
    def get_csv_filename(self):
        return '%s - J+S.csv' % self.object.number

    def write_csv(self, filelike):
        return self.object.get_js_csv(filelike)


class CourseParticipantsView(CourseDetailView):
    template_name = 'mailer/pdf_participants_list.html'

    def get_context_data(self, **kwargs):
        context = super(CourseParticipantsView, self).get_context_data(**kwargs)
        context['sessions'] = list(range(0, self.object.number_of_sessions))
        return context

    def get_template_names(self):
        return self.template_name


class CourseListView(BackendMixin, ListView):
    model = Course
    queryset = Course.objects.select_related('activity').prefetch_related('participants', 'instructors')

    def get_template_names(self):
        if self.request.PHASE == 1:
            return 'backend/course/list-phase1.html'
        return 'backend/course/list.html'


class CourseParticipantsExportView(BackendMixin, SingleObjectMixin, ExcelResponseMixin, View):
    model = Course
    pk_url_kwarg = 'course'

    def get_filename(self):
        return self.object.number

    def get_resource(self):
        return RegistrationResource(course=self.object)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response()


class PaySlipMontreux(BackendMixin, CreateView):
    template_name = 'backend/course/pay-slip-montreux-form.html'
    form_class = PaySlipForm

    def get_initial(self):
        course = get_object_or_404(Course, pk=self.kwargs['course'])
        session_dates = course.sessions.values_list('date', flat=True)
        initial = {}
        instructor = get_object_or_404(FamilyUser, pk=self.kwargs['instructor'])
        course = get_object_or_404(Course, pk=self.kwargs['course'])
        from activities.models import CoursesInstructors
        try:
            courses_instructor = CoursesInstructors.objects.get(course=course, instructor=instructor)
            function = courses_instructor.function
            if function:
                initial['function'] = '%s (%s)' % (function.name, function.code)
                initial['rate_mode'] = function.rate_mode
                initial['rate'] = function.rate

        except CoursesInstructors.DoesNotExist:
            initial['function'] = ''

        if session_dates:
            initial['start_date'] = min(session_dates)
            initial['end_date'] = max(session_dates)
        return initial

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        context = self.get_context_data(**kwargs)
        self.object.course = context['course']
        self.object.instructor = context['instructor']
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        kwargs = super(PaySlipMontreux, self).get_context_data(**kwargs)
        kwargs['instructor'] = get_object_or_404(FamilyUser, pk=self.kwargs['instructor'])
        kwargs['course'] = get_object_or_404(Course, pk=self.kwargs['course'])
        return super(PaySlipMontreux, self).get_context_data(**kwargs)
