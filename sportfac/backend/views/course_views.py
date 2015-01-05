from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

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
   


class CourseCreateView(BackendMixin, CreateView):
    form_class = CourseForm
    template_name = 'backend/course/create.html'


class CourseUpdateView(BackendMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'backend/course/update.html'
    
    
class CourseDeleteView(BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course/confirm_delete.html'
    success_url = reverse_lazy('backend:course-list')

