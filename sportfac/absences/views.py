from django.shortcuts import render
from django.views.generic import DetailView, ListView

from activities.views import ResponsibleMixin
from activities.models import Course
from .models import Session


class AbsenceView(ResponsibleMixin, DetailView):
    model = Course
    template_name = 'absences/absences.html'
    pk_url_kwarg = 'course'
    queryset = Course.objects.prefetch_related('sessions')