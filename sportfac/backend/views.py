from django.shortcuts import render
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                 ListView, UpdateView

from . import GROUP_NAME
from activities.models import Course

from braces.views import GroupRequiredMixin, LoginRequiredMixin


class BackendMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports managers group."""
    group_required = GROUP_NAME

class CourseDetailView(BackendMixin, DetailView):
    model = Course
    template_name = 'backend/course_detail.html'

class CourseListView(BackendMixin, ListView):
    model = Course
    template_name = 'backend/course_list.html'
   

class CourseCreateView(BackendMixin, CreateView):
    model = Course
    fields = ('activity', 'number', 'responsible', 'price', 
              'number_of_sessions', 'day', 'start_date', 'end_date',
              'start_time', 'end_time', 'place', 'min_participants',
              'max_participants', 'schoolyear_min', 'schoolyear_max')
    template_name = 'backend/course_form.html'

class CourseUpdateView(BackendMixin, UpdateView):
    model = Course
    fields = ('activity', 'number', 'responsible', 'price', 
              'number_of_sessions', 'day', 'start_date', 'end_date',
              'start_time', 'end_time', 'place', 'min_participants',
              'max_participants', 'schoolyear_min', 'schoolyear_max')
    template_name = 'backend/course_form.html'
    
class CourseDeleteView(BackendMixin, DeleteView):
    model = Course
    template_name = 'backend/course_confirm_delete.html'
    success_url = reverse_lazy('backend:course-list')