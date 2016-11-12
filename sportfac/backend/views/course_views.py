from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from absences.models import Absence
from activities.models import Course, Activity
from activities.forms import CourseForm
from sportfac.views import CSVMixin
from .mixins import BackendMixin

__all__ = ('CourseCreateView', 'CourseDeleteView', 'CourseDetailView',
           'CourseJSCSVView', 'CourseAbsenceView',
           'CourseListView', 'CourseUpdateView', 'CourseParticipantsView')


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'
    #slug_field = 'number'
    #slug_url_kwarg = 'course'
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
            [((absence.child, absence.session), absence.status) for absence 
                                                                in Absence.objects.filter(session__course=course)]
        )
        context['absence_matrix'] = [[all_absences.get((registration.child, session), 'present') for session 
                                                                     in course.sessions.all()] 
         for registration in course.participants.all()]

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
    queryset = Course.objects.select_related('activity').\
                              prefetch_related('participants', 'instructors')
    
    def get_template_names(self):
        if self.request.PHASE == 1:
            return 'backend/course/list-phase1.html'
        return 'backend/course/list.html'


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
        return super(CourseCreateView, self).form_valid(form)


class CourseUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'backend/course/update.html'
    #slug_field = 'number'
    #slug_url_kwarg = 'course'
    pk_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')
    
    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})
    def form_valid(self, form):
        course = self.get_object()
        removed_instructors = set(course.instructors.all()) - set(form.cleaned_data['instructors'])
        response = super(CourseUpdateView, self).form_valid(form)
        
        for instructor in removed_instructors:
            if instructor.course.exclude(pk=course.pk).count() == 0:
                instructor.is_instructor = False
            
        for user in form.cleaned_data['instructors']:
            user.is_instructor = True
        return response


class CourseDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
    #slug_field = 'number'
    #slug_url_kwarg = 'course'
    pk_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _("Course has been deleted.")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.add_message(self.request, messages.SUCCESS,
                             _("Course %(identifier)s has been deleted.") % {
                                'identifier': identifier
                             })
        for instructor in self.object.instructors.all():
            if instructor.course.exclude(pk=self.object.pk).count() == 0:
                instructor.is_instructor = False
        return super(CourseDeleteView, self).delete(request, *args, **kwargs)
