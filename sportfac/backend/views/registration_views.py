from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.views.generic import DeleteView, DetailView, \
                                ListView, UpdateView
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from django.shortcuts import get_object_or_404

from formtools.wizard.views import SessionWizardView

from activities.models import Course
from registrations.models import Bill, Registration, ExtraInfo
from registrations.forms import BillForm
from registrations.views import BillMixin
from backend.forms import BillingForm, ChildSelectForm, CourseSelectForm, RegistrationForm, ExtraInfoFormSet
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
        return Registration.objects.select_related('course', 'child', 'child__family').prefetch_related('course__activity').all()

def show_extra_questions(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(_('Course')) or {}
    course = cleaned_data.get('course')
    if course and course.extra.count():
        return True
    return False

class RegistrationCreateView(BackendMixin, SessionWizardView):
    form_list = ((_('Child'), ChildSelectForm),
                 (_('Course'), CourseSelectForm),
                 #(_('Questions'), CourseSelectForm),
                 (_('Billing'), BillingForm)
                )
    #condition_dict = {_('Extra questions'): show_extra_questions}
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
                status = Bill.STATUS.waiting
                if self.instance.course.price == 0:
                    status = Bill.STATUS.paid
                bill = Bill.objects.create(
                    status=status,
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
        return HttpResponseRedirect(self.instance.course.get_backend_url())
    
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

    def get_context_data(self, **kwargs):
        context = super(RegistrationUpdateView, self).get_context_data(**kwargs)
        object = self.get_object()
        extras = {}
        courses = Course.objects.prefetch_related('extra').annotate(nb_extra=Count('extra'))
        for course in courses.exclude(nb_extra=0):
            extras[course.id] = course.extra.all()
        context['extra_questions'] = extras
        context['need_extra'] = object.course.id in extras
        return context

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        for question in self.object.course.extra.all():
            try:
                self.object.extra_infos.get(key=question)
            except ExtraInfo.DoesNotExist:
                ExtraInfo.objects.create(registration=self.object, key=question, value=question.default)
        extrainfo_form = ExtraInfoFormSet(instance=self.object)
        return self.render_to_response(self.get_context_data(form=form, extrainfo_form=extrainfo_form))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        extrainfo_form = ExtraInfoFormSet(self.request.POST, instance=self.object)
        if form.is_valid() and extrainfo_form.is_valid():
            return self.form_valid(form, extrainfo_form)
        return self.form_invalid(form, extrainfo_form)

    @transaction.atomic
    def form_valid(self, form, extrainfo_form):
        self.object = form.save()
        extrainfo_form.instance = self.object
        extrainfo_form.save()
        if self.object.status == Registration.STATUS.confirmed and not self.object.paid and not self.object.bill:
            status = Bill.STATUS.waiting
            if self.object.course.price == 0:
                status = Bill.STATUS.paid
            bill = Bill.objects.create(
                status=status,
                family=self.request.user,
            )

            self.object.bill = bill
            self.object.save()
            bill.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, extrainfo_form):
        return self.render_to_response(self.get_context_data(form=form, extrainfo_form=extrainfo_form))

class RegistrationDeleteView(BackendMixin, DeleteView):
    model = Registration
    template_name = 'backend/registration/confirm_delete.html'

    def get_success_url(self):
        return self.object.course.get_backend_url()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.cancel()
            self.object.save()
        except IntegrityError:
            # The registration for child and course existed previously and 
            # was already canceled. We do not need to cancel it again
            self.object.delete()
        messages.add_message(self.request, messages.SUCCESS, 
                             _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)


class BillListView(BackendMixin, ListView):
    model = Bill
    template_name = 'backend/registration/bill-list.html'
    
    def get_queryset(self):
        return Bill.objects.all().select_related('family').order_by('status', 'billing_identifier')
    
 
class BillDetailView(BackendMixin, BillMixin, DetailView):
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