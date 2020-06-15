# -*- coding: utf-8 -*-
from django.contrib.flatpages.models import FlatPage

from .mixins import BackendMixin

from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView, View


class FlatPageListView(BackendMixin, ListView):
    model = FlatPage
    template_name = 'backend/site/flatpage_list.html'
