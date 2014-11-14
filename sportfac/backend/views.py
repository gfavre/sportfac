from django.shortcuts import render
from django.views.generic import DetailView

from activities.models import Course

from braces.views import PermissionRequiredMixin. LoginRequiredMixin

class BackendView(PermissionRequiredMixin, LoginRequiredMixin):
    permission_required = ''

