# -*- coding: utf-8 -*-
from django.contrib.flatpages.models import FlatPage
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from django.views.generic import ListView, UpdateView

from ..forms import FlatPageForm
from .mixins import BackendMixin


class FlatPageListView(BackendMixin, ListView):
    model = FlatPage
    template_name = 'backend/site/flatpage_list.html'


class FlatPageUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = FlatPage
    form_class = FlatPageForm
    template_name = 'backend/site/flatpage_update.html'
    success_url = reverse_lazy('backend:flatpages-list')
    success_message = _('<a href="%(url)s" class="alert-link">Page "%(title)s"</a> has been updated.')

    def get_success_message(self, cleaned_data):
        url = self.success_url
        return mark_safe(
            self.success_message % {'url': self.object.url,
                                    'title': cleaned_data.get('title')}
        )
