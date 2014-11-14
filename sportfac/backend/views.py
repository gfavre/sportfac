from django.shortcuts import render
from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                 ListView, UpdateView

from . import GROUP_NAME
from activities.models import Course, Activity, Responsible

from braces.views import GroupRequiredMixin, LoginRequiredMixin


class BackendMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports managers group."""
    group_required = GROUP_NAME

################################################################################
# Courses
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



################################################################################
# Responsibles
class ResponsibleDetailView(BackendMixin, DetailView):
    model = Responsible
    template_name = 'backend/responsible/detail.html'

class ResponsibleListView(BackendMixin, ListView):
    model = Responsible
    template_name = 'backend/responsible/list.html'
   

class ResponsibleCreateView(BackendMixin, CreateView):
    model = Responsible
    fields = ('first', 'last', 'phone', 'email')
    template_name = 'backend/responsible/create.html'

class ResponsibleUpdateView(BackendMixin, UpdateView):
    model = Responsible
    fields = ('first', 'last', 'phone', 'email')
    template_name = 'backend/responsible/update.html'
    
class ResponsibleDeleteView(BackendMixin, DeleteView):
    model = Responsible
    template_name = 'backend/responsible/confirm_delete.html'
    success_url = reverse_lazy('backend:responsible-list')


################################################################################
# Activities
class ActivityDetailView(BackendMixin, DetailView):
    model = Activity
    template_name = 'backend/activity/detail.html'

class ActivityListView(BackendMixin, ListView):
    model = Activity
    template_name = 'backend/activity/list.html'
   

class ActivityCreateView(BackendMixin, CreateView):
    model = Activity
    fields = ('name', 'number', 'informations', 'description')
    template_name = 'backend/activity/create.html'

class ActivityUpdateView(BackendMixin, UpdateView):
    model = Activity
    fields = ('name', 'number', 'informations', 'description')
    template_name = 'backend/activity/update.html'
    
class ActivityDeleteView(BackendMixin, DeleteView):
    model = Activity
    template_name = 'backend/activity/confirm_delete.html'
    success_url = reverse_lazy('backend:activity-list')
