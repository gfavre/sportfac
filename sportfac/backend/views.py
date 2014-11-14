from django.shortcuts import render
from django.views.generic import DetailView

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