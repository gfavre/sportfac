from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.translation import ugettext as _

from profiles.models import Registration

from .mixins import BackendMixin
from backend.forms import RegistrationForm, RegistrationUpdateForm

   

class RegistrationDetailView(BackendMixin, DetailView):
    model = Registration
    template_name = 'backend/registration/detail.html'




class RegistrationListView(BackendMixin, ListView):
    model = Registration
    template_name = 'backend/registration/list.html'
    
    def get_queryset(self):
        return Registration.objects.select_related('course', 'child').prefetch_related('course__activity').all()

   

class RegistrationCreateView(BackendMixin, CreateView):
    model = Registration
    form_class = RegistrationForm
    template_name = 'backend/registration/create.html'


class RegistrationUpdateView(BackendMixin, UpdateView):
    model = Registration
    form_class = RegistrationUpdateForm
    template_name = 'backend/registration/update.html'

    


class RegistrationDeleteView(BackendMixin, DeleteView):
    model = Registration
    template_name = 'backend/registration/confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('backend:course-detail', kwargs={'pk': self.object.course.pk})
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.cancel()
        self.object.save()
        messages.add_message(self.request, messages.SUCCESS, 
                             _("Registration has been canceled."))

        return HttpResponseRedirect(success_url)
