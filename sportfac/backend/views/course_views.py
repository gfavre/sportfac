# -*- coding: utf-8 -*-
from decimal import Decimal

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView, View
from django.views.generic.detail import SingleObjectMixin

from absences.models import Absence
from activities.models import Course, Activity
from activities.forms import CourseForm
from profiles.models import FamilyUser
from registrations.models import Registration
from registrations.resources import RegistrationResource
from sportfac.views import CSVMixin
from .mixins import BackendMixin, ExcelResponseMixin
from ..forms import PayslipMontreuxForm

__all__ = ('CourseCreateView', 'CourseDeleteView', 'CourseDetailView',
           'CourseJSCSVView', 'CourseParticipantsExportView', 'CourseAbsenceView',
           'CourseListView', 'CourseUpdateView', 'CourseParticipantsView',
           'PaySlipMontreux')


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity')\
                             .prefetch_related('participants__child__school_year',
                                               'participants__child__family',
                                               'instructors')

    def get_template_names(self):
        if self.request.PHASE == 2:
            return 'backend/course/detail-phase2.html'
        return 'backend/course/detail.html'

    def get_context_data(self, **kwargs):
        context = super(CourseDetailView, self).get_context_data(**kwargs)
        registrations = self.get_object().participants.all()
        context['registrations'] = registrations
        return context


class CourseAbsenceView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/absences.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.prefetch_related('sessions', 'sessions__absences', 'participants__child')
    
    def get_context_data(self, **kwargs):
        context = super(CourseAbsenceView, self).get_context_data(**kwargs)
        course = self.get_object()
        all_absences = dict(
            [((absence.child, absence.session), absence.status)
             for absence in Absence.objects.filter(session__course=course)]
        )
        context['absence_matrix'] = [
            [all_absences.get((registration.child, session), 'present') for session in course.sessions.all()]
            for registration in course.participants.all()
        ]
        context['courses_list'] = Course.objects.all()
        context['levels'] = Registration.LEVELS

        return context


class CourseJSCSVView(CSVMixin, CourseDetailView):
    def get_csv_filename(self):
        return '%s - J+S.csv' % self.object.number
    
    def write_csv(self, filelike):
        return self.object.get_js_csv(filelike)
    

class CourseParticipantsView(CourseDetailView):
    template_name = 'mailer/pdf_participants_list.html'

    def get_context_data(self, **kwargs):
        context = super(CourseParticipantsView, self).get_context_data(**kwargs)
        context['sessions'] = range(0, self.object.number_of_sessions)
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


class CourseCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    form_class = CourseForm
    template_name = 'backend/course/create.html'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been created.')
    
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
        return initial

    def form_valid(self, form):
        for user in form.cleaned_data['instructors']:
            user.is_instructor = True
            user.save()
        self.object = form.save()
        for extra in form.cleaned_data['extra']:
            self.object.extra.add(extra)
        return HttpResponseRedirect(self.get_success_url())


class CourseUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'backend/course/update.html'
    pk_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')
    
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
        removed_instructors = set(course.instructors.all()) - set(form.cleaned_data['instructors'])
        response = super(CourseUpdateView, self).form_valid(form)
        
        for instructor in removed_instructors:
            if instructor.course.exclude(pk=course.pk).count() == 0:
                instructor.is_instructor = False
            
        for user in form.cleaned_data['instructors']:
            user.is_instructor = True

        removed_extras = set(course.extra.all()) - set(form.cleaned_data['extra'])
        for removed_extra in removed_extras:
            course.extra.remove(removed_extra)
        for extra in form.cleaned_data['extra']:
            course.extra.add(extra)
        return response


class CourseDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/transport/confirm_delete.html'
    success_url = reverse_lazy('backend:transport-list')
    success_message = _("Transport has been deleted.")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().name
        messages.add_message(self.request, messages.SUCCESS,
                             _("Transport %(identifier)s has been deleted.") % {
                                'identifier': identifier
                             })
        return super(CourseDeleteView, self).delete(request, *args, **kwargs)


class PaySlipMontreux(BackendMixin, FormView):
    template_name = 'backend/course/pay-slip-montreux-form.html'
    form_class = PayslipMontreuxForm

    def form_valid(self, form, **kwargs):
        context = self.get_context_data(**kwargs)
        context['rate'] = Decimal(form.cleaned_data['rate'])
        context['rate_mode'] = form.cleaned_data['rate_mode']
        context['function'] = form.cleaned_data['function']

        if form.cleaned_data['rate_mode'] == 'hour':
            duration = context['course'].duration
            hours = duration.seconds / 3600.0 + duration.days * 24
            context['amount'] = Decimal(context['rate']) * Decimal(context['sessions'].count()) * hours
        else:
            context['amount'] = Decimal(context['sessions'].count()) * context['rate']

        return TemplateResponse(
            request=self.request,
            template=['backend/course/pay-slip-montreux.html'],
            context=context
        )

    def form_invalid(self, form, **kwargs):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(form=form, **kwargs))

    def get_context_data(self, **kwargs):
        kwargs['instructor'] = get_object_or_404(FamilyUser, pk=kwargs['instructor'])
        kwargs['course'] = get_object_or_404(Course, pk=kwargs['course'])
        kwargs['sessions'] = kwargs['course'].sessions.filter(instructor=kwargs['instructor'])
        total_presentees = sum([session.presentees_nb() for session in kwargs['sessions']])
        kwargs['avg'] = round(float(total_presentees) / max(len(kwargs['sessions']), 1), 1)
        return super(PaySlipMontreux, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form, **kwargs)
        else:
            return self.form_invalid(form, **kwargs)
