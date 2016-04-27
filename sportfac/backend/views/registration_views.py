from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect
from django.views.generic import DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError

from formtools.wizard.views import SessionWizardView

from activities.models import Course
from registrations.models import Registration
from backend.forms import ChildSelectForm, CourseSelectForm, RegistrationForm
from .mixins import BackendMixin

__all__ = ('RegistrationCreateView', 'RegistrationDeleteView', 'RegistrationDetailView', 
           'RegistrationListView', 'RegistrationUpdateView',)


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
        user = self.instance.child.family
        user.finished_registration = True
        user.save()
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
    form_class = RegistrationForm
    template_name = 'backend/registration/update.html'
    success_message = _("Registration has been updated.")
    success_url = reverse_lazy('backend:registration-list')
            
    def get_success_url(self):
        course = self.request.GET.get('course', None)
        if not course:
            return self.success_url
        else:
            course_obj = get_object_or_404(Course, number=course)
            return course_obj.get_backend_url()

class RegistrationDeleteView(BackendMixin, DeleteView):
    model = Registration
    template_name = 'backend/registration/confirm_delete.html'

    def get_success_url(self):
        return self.object.course.get_backend_url()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        self.object.cancel()
        self.object.save()
        messages.add_message(self.request, messages.SUCCESS, 
                             _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)
