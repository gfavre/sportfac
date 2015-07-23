from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
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
    slug_field = 'slug'
    slug_url_kwarg = 'activity'
    template_name = 'backend/activity/detail.html'


class ActivityListView(BackendMixin, ListView):
    model = Activity
    template_name = 'backend/activity/list.html'


class ActivityCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    success_url = reverse_lazy('backend:activity-list')
    success_message = _('<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been created.')
    template_name = 'backend/activity/create.html'

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})


class ActivityUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    slug_field = 'slug'
    slug_url_kwarg = 'activity'
    success_url = reverse_lazy('backend:activity-list')
    success_message = _('<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been updated.')
    template_name = 'backend/activity/update.html'

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {'url': url,
                                                 'number': self.object.number})


class ActivityDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Activity
    slug_field = 'slug'
    slug_url_kwarg = 'activity'
    success_message = _("Activity has been deleted.")
    success_url = reverse_lazy('backend:activity-list')
    template_name = 'backend/activity/confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.add_message(self.request, messages.SUCCESS,
                             _("Activity %(identifier)s has been deleted.") % {
                                'identifier': identifier
                             })
        return super(ActivityDeleteView, self).delete(request, *args, **kwargs)
    
