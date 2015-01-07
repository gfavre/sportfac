from django.core.urlresolvers import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView

from activities.models import Responsible

from .mixins import BackendMixin


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
