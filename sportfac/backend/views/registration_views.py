from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.views.generic import DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from django.shortcuts import get_object_or_404

from formtools.wizard.views import SessionWizardView

from activities.models import Course
from registrations.models import Bill, Registration
from registrations.forms import BillForm
from backend.forms import BillingForm, ChildSelectForm, CourseSelectForm, RegistrationForm
from .mixins import BackendMixin


__all__ = ('RegistrationCreateView', 'RegistrationDeleteView', 'RegistrationDetailView', 
           'RegistrationListView', 'RegistrationUpdateView',
           'BillListView', 'BillDetailView', 'BillUpdateView')


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
                 (_('Course'), CourseSelectForm),
                 (_('Billing'), BillingForm)
                )
    template_name = 'backend/registration/wizard.html'
    instance = None
    
    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        self.instance.status = Registration.STATUS.confirmed
        user = self.instance.child.family
        message = _("Registration for %(child)s to %(course)s has been validated.")
        message %= {'child': self.instance.child,
                    'course': self.instance.course.short_name}
        messages.add_message(self.request, messages.SUCCESS, message)

        try:
            if not self.instance.paid:
                bill = Bill.objects.create(
                    status=Bill.STATUS.waiting,
                    family=user 
                )
                bill.update_billing_identifier()
                bill.save()
                self.instance.bill = bill
                message = _('The bill %(identifier)s has been created. <a href="%(url)s">Please review it.</a>')   
                message = mark_safe(message % {'identifier': bill.billing_identifier, 
                                               'url': bill.backend_url})
                messages.add_message(self.request, messages.INFO, message)
            self.instance.save()
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


class BillListView(BackendMixin, ListView):
    model = Bill
    template_name = 'backend/registration/bill-list.html'
    
    def get_queryset(self):
        return Bill.objects.all().select_related('family').order_by('status', 'billing_identifier')
    
 
class BillDetailView(BackendMixin, DetailView):
    model = Bill
    template_name = 'backend/registration/bill-detail.html'


class BillUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Bill
    form_class = BillForm
    template_name = 'backend/registration/bill-update.html'
    success_message = _("Bill has been updated.")
    success_url = reverse_lazy('backend:bill-list')
    
    def form_valid(self, form):
        if form.cleaned_data['status'] == Bill.STATUS.paid:
            self.object.close()
            self.object.save()
        else:
            self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())