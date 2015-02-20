from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin

from activities.models import Course
from activities.forms import CourseForm
from sportfac.views import CSVMixin
from .mixins import BackendMixin

__all__ = ('CourseCreateView', 'CourseDeleteView', 'CourseDetailView',
           'CourseJSCSVView',
           'CourseListView', 'CourseUpdateView', 'CourseParticipantsView')


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'
    slug_field = 'number'
    slug_url_kwarg = 'course'
    queryset = Course.objects.select_related('activity', 'responsible')\
                             .prefetch_related('participants__child__school_year',
                                               'participants__child__family')

class CourseJSCSVView(CSVMixin, CourseDetailView):
    def get_csv_filename(self):
        return '%s - J+S.csv' % self.object.number
    
    def write_csv(self, filelike):
        return self.object.get_js_csv(filelike)
        
    

class CourseParticipantsView(CourseDetailView):
    template_name = 'mailer/pdf_participants_presence.html'

    def get_context_data(self, **kwargs):
        context = super(CourseParticipantsView, self).get_context_data(**kwargs)
        context['sessions'] = range(0, self.object.number_of_sessions)
        return context


class CourseListView(BackendMixin, ListView):
    model = Course
    queryset = Course.objects.select_related('activity', 'responsible').prefetch_related('participants')
    
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


class CourseUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'backend/course/update.html'
    slug_field = 'number'
    slug_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')
    
    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})


class CourseDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
    slug_field = 'number'
    slug_url_kwarg = 'course'
    success_url = reverse_lazy('backend:course-list')
    success_message = _("Course has been deleted.")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.add_message(self.request, messages.SUCCESS,
                             _("Course %(identifier)s has been deleted.") % {
                                'identifier': identifier
                             })
        return super(CourseDeleteView, self).delete(request, *args, **kwargs)
