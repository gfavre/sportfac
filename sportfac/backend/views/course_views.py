from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from activities.models import Course

from .mixins import BackendMixin


class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course/detail.html'

class CourseListView(BackendMixin, ListView):
    model = Course
    template_name = 'backend/course/list.html'
   

class CourseCreateView(BackendMixin, CreateView):
    model = Course
    fields = ('activity', 'number', 'responsible', 'price', 
              'number_of_sessions', 'day', 'start_date', 'end_date',
              'start_time', 'end_time', 'place', 'min_participants',
              'max_participants', 'schoolyear_min', 'schoolyear_max')
    template_name = 'backend/course/create.html'

class CourseUpdateView(BackendMixin, UpdateView):
    model = Course
    fields = ('activity', 'number', 'responsible', 'price', 
              'number_of_sessions', 'day', 'start_date', 'end_date',
              'start_time', 'end_time', 'place', 'min_participants',
              'max_participants', 'schoolyear_min', 'schoolyear_max')
    template_name = 'backend/course/update.html'
    
class CourseDeleteView(BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
    success_url = reverse_lazy('backend:course-list')

