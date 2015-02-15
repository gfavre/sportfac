from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from activities.models import Activity
from activities.forms import ActivityForm

from .mixins import BackendMixin

__all__ = ['ActivityDetailView', 'ActivityListView',
           'ActivityCreateView',  'ActivityUpdateView',
           'ActivityDeleteView']


class ActivityDetailView(BackendMixin, DetailView):
    model = Activity
    template_name = 'backend/activity/detail.html'


class ActivityListView(BackendMixin, ListView):
    model = Activity
    template_name = 'backend/activity/list.html'


class ActivityCreateView(BackendMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    template_name = 'backend/activity/create.html'


class ActivityUpdateView(BackendMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    template_name = 'backend/activity/update.html'


class ActivityDeleteView(BackendMixin, DeleteView):
    model = Activity
    template_name = 'backend/activity/confirm_delete.html'
    success_url = reverse_lazy('backend:activity-list')
