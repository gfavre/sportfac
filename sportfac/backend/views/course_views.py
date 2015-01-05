from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.contrib.messages.views import SuccessMessageMixin

from activities.models import Course
from activities.forms import CourseForm

from .mixins import BackendMixin


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'
    queryset = Course.objects.select_related('activity', 
                                             'responsible', 
                                             #'participants__child',
                                             #'participants__child__family'
                            ).prefetch_related( 'participants__child__school_year', 'participants__child__family')


class CourseListView(BackendMixin, ListView):
    model = Course
    queryset = Course.objects.select_related('activity', 'responsible').prefetch_related('participants')
    template_name = 'backend/course/list.html'
   


class CourseCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    form_class = CourseForm
    template_name = 'backend/course/create.html'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been created.')
    
    def get_success_message(self, cleaned_data):    
        url = reverse('backend:course-detail', kwargs={'pk': self.object.pk})
        return mark_safe(self.success_message % {'url': url, 'number': self.object.number})


class CourseUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'backend/course/update.html'
    success_url = reverse_lazy('backend:course-list')
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')
    
    def get_success_message(self, cleaned_data):    
        url = reverse('backend:course-detail', kwargs={'pk': self.object.pk})
        return mark_safe(self.success_message % {'url': url, 'number': self.object.number})

    
class CourseDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
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
