from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import CreateView, DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.translation import ugettext_lazy as _
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.formtools.wizard.views import SessionWizardView
from django.db import IntegrityError

from profiles.models import Registration

from .mixins import BackendMixin

from backend.forms import RegistrationForm, ChildSelectForm, CourseSelectForm

   

class RegistrationDetailView(BackendMixin, DetailView):
    model = Registration
    template_name = 'backend/registration/detail.html'




class RegistrationListView(BackendMixin, ListView):
    model = Registration
    template_name = 'backend/registration/list.html'
    
    def get_queryset(self):
        return Registration.objects.select_related('course', 'child').prefetch_related('course__activity').all()

   


class RegistrationCreateView(BackendMixin, SessionWizardView):
    form_list = ((_('Child'), ChildSelectForm),
                 (_('Course'), CourseSelectForm),)
    template_name = 'backend/registration/wizard.html'
    instance = None
    
    def done(self, form_list, form_dict, **kwargs):
        self.instance.status = Registration.STATUS.confirmed
        try:
            self.instance.save()
            message = _("Registration for %(child)s to %(course)s has been validated.")
            message %= {'child': self.instance.child,
                        'course': self.instance.course.short_name}
            messages.add_message(self.request, messages.SUCCESS, message)
        except IntegrityError:
            message = _("A registration for %(child)s to %(course)s already exists.")
            message %= {'child': self.instance.child,
                        'course': self.instance.course.short_name}
            messages.add_message(self.request, messages.WARNING, message)
        return HttpResponseRedirect(reverse_lazy('backend:registration-list'))
    
    def get_form_instance(self, step):
        if self.instance is None:
            self.instance = Registration()
        return self.instance


class RegistrationUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Registration
    form_class = CourseSelectForm
    template_name = 'backend/registration/update.html'
    success_message = _("Registration has been updated.")

    def get_success_url(self):
        return reverse_lazy('backend:course-detail', kwargs={'pk': self.initial_object.course.pk})
    
            
    def form_valid(self, form):
        self.initial_object = Registration.objects.get(pk=self.object.pk)
        form.instance.status = Registration.STATUS.confirmed
        return super(RegistrationUpdateView, self).form_valid(form)
    
 

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
