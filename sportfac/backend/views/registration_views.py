# -*- coding: utf-8 -*-
import collections

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.urlresolvers import reverse_lazy
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.views.generic import (CreateView, DeleteView, DetailView, ListView, UpdateView,
                                  View, FormView)
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from formtools.wizard.views import SessionWizardView

from absences.models import Absence
from activities.models import Course, ExtraNeed
from backend.forms import (BillingForm, ChildSelectForm, CourseSelectForm,
                           RegistrationForm, ExtraInfoFormSet)
from registrations.resources import RegistrationResource
from registrations.models import Bill, Registration, ExtraInfo, Transport
from registrations.forms import BillForm, MoveRegistrationsForm, MoveTransportForm, TransportForm
from registrations.views import BillMixin
from .mixins import BackendMixin, ExcelResponseMixin

__all__ = ('RegistrationCreateView', 'RegistrationDeleteView', 'RegistrationDetailView',
           'RegistrationListView', 'RegistrationExportView', 'RegistrationUpdateView',
           'RegistrationsMoveView',
           'BillListView', 'BillDetailView', 'BillUpdateView',
           'TransportListView', 'TransportCreateView', 'TransportUpdateView',
           'TransportDetailView', 'TransportDeleteView', 'TransportMoveView',)


class RegistrationDetailView(BackendMixin, DetailView):
    model = Registration
    template_name = 'backend/registration/detail.html'


class RegistrationListView(BackendMixin, ListView):
    model = Registration
    template_name = 'backend/registration/list.html'

    def get_queryset(self):
        return Registration.objects.select_related('course', 'child', 'child__family')\
                                   .prefetch_related('course__activity')


class RegistrationExportView(BackendMixin, ExcelResponseMixin, View):
    filename = _("registrations")

    def get_resource(self):
        return RegistrationResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class RegistrationsMoveView(BackendMixin, FormView):
    form_class = MoveRegistrationsForm
    template_name = 'backend/registration/move.html'

    def form_valid(self, form):
        course = form.cleaned_data['destination']
        origin = form.cleaned_data['registrations'].first().course
        form.cleaned_data['registrations'].update(course=course,
                                                  status=Registration.STATUS.confirmed)
        message = _("Registrations of %(nb)s children have been moved.")
        message %= {'nb': form.cleaned_data['registrations'].count()}
        messages.add_message(self.request, messages.SUCCESS, message)
        return HttpResponseRedirect(origin.backend_url)

    def get_context_data(self, **kwargs):
        try:
            prev = int(self.request.GET.get('prev'))
        except (IndexError, TypeError):
            prev = None
        kwargs['origin'] = None
        if prev:
            try:
                kwargs['origin'] = Course.objects.get(pk=prev)
            except Course.DoesNotExist:
                pass
        form = self.get_form()
        form.is_valid()
        kwargs['children'] = [reg.child for reg in form.cleaned_data.get('registrations', [])]
        return super(RegistrationsMoveView, self).get_context_data(**kwargs)


def show_extra_questions(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(_('Course')) or {}
    course = cleaned_data.get('course')
    if course and course.extra.count():
        return True
    return False


class RegistrationCreateView(BackendMixin, SessionWizardView):
    form_list = (
        (_('Child'), ChildSelectForm),
        (_('Course'), CourseSelectForm),
        # (_('Questions'), CourseSelectForm),
        (_('Billing'), BillingForm)
    )
    # condition_dict = {_('Extra questions'): show_extra_questions}
    template_name = 'backend/registration/wizard.html'
    instance = None

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        self.instance.status = Registration.STATUS.confirmed
        user = self.instance.child.family
        message = _("Registration for %(child)s to %(course)s has been validated.")
        message %= {
            'child': self.instance.child,
            'course': self.instance.course.short_name
        }
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
            course_obj = get_object_or_404(Course, pk=course)
            return course_obj.get_backend_url()

    def get_context_data(self, **kwargs):
        context = super(RegistrationUpdateView, self).get_context_data(**kwargs)
        extras = {}
        courses = Course.objects.prefetch_related('extra').annotate(nb_extra=Count('extra'))
        for course in courses.exclude(nb_extra=0):
            extras[course.id] = course.extra.all()
        context['extra_questions'] = extras
        context['need_extra'] = self.object.course.id in extras
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
                family=self.object.child.family,
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
        self.object = self.get_object()
        if form.cleaned_data['status'] == Bill.STATUS.paid:
            self.object.close()
            self.object.save()
        else:
            form.save()
        return HttpResponseRedirect(self.get_success_url())


class TransportListView(BackendMixin, ListView):
    model = Transport
    template_name = 'backend/registration/transport-list.html'


class TransportDetailView(BackendMixin, DetailView):
    model = Transport
    template_name = 'backend/registration/transport-detail.html'
    queryset = Transport.objects.prefetch_related('participants', 'participants__child', 'participants__course')

    def get_context_data(self, **kwargs):
        courses = set([registration.course for registration in self.object.participants.all()])
        children = set([registration.child for registration in self.object.participants.all()])
        registrations = dict([((registration.child, registration.course), registration) for registration in self.object.participants.all()])
        qs = Absence.objects.filter(session__course__in=courses, child__in=children) \
                            .select_related('session', 'child', 'session__course', 'session__course__activity') \
                            .order_by('child__last_name', 'child__first_name')
        kwargs['all_dates'] = list(set(qs.values_list('session__date', flat=True)))
        kwargs['all_dates'].sort(reverse=True)
        try:
            questions = ExtraNeed.objects.filter(question_label__startswith=u'Arrêt')
            all_extras = dict([(extra.registration.child, extra.value) for extra in ExtraInfo.objects.filter(
                registration__child__in=children,
                registration__course__in=courses,
                key__in=questions)])
        except ExtraNeed.DoesNotExist:
            all_extras = {}

        child_absences = collections.OrderedDict()
        for absence in qs:
            child = absence.child
            course = absence.session.course
            if (child, course) not in registrations:
                # another child in same course
                continue
            child.bus_stop = all_extras.get(child, '')
            the_tuple = (child, course, registrations[(child, course)])
            if the_tuple in child_absences:
                child_absences[the_tuple][absence.session.date] = absence
            else:
                child_absences[the_tuple] = {absence.session.date: absence}
        kwargs['child_absences'] = child_absences

        return super(TransportDetailView, self).get_context_data(**kwargs)


class TransportCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = Transport
    form_class = TransportForm
    template_name = 'backend/registration/transport-create.html'
    success_url = reverse_lazy('backend:transport-list')
    success_message = _('Transport has been created.')


class TransportUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Transport
    form_class = TransportForm
    template_name = 'backend/registration/transport-update.html'
    success_message = _('Transport has been updated.')
    success_url = reverse_lazy('backend:transport-list')


class TransportDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Transport
    template_name = 'backend/registration/transport_confirm_delete.html'
    success_url = reverse_lazy('backend:transport-list')
    success_message = _("Transport has been deleted.")


class TransportMoveView(BackendMixin, FormView):
    form_class = MoveTransportForm
    template_name = 'backend/registration/move.html'

    def form_valid(self, form):
        transport = form.cleaned_data['destination']
        form.cleaned_data['registrations'].update(transport=transport,
                                                  status=Registration.STATUS.confirmed)
        message = _("Registrations of %(nb)s children have been moved.")
        message %= {'nb': form.cleaned_data['registrations'].count()}
        messages.add_message(self.request, messages.SUCCESS, message)
        return HttpResponseRedirect(transport.backend_url)

    def get_context_data(self, **kwargs):
        try:
            prev = int(self.request.GET.get('prev'))
        except (IndexError, TypeError):
            prev = None
        kwargs['origin'] = None
        if prev:
            try:
                kwargs['origin'] = Transport.objects.get(pk=prev)
            except Transport.DoesNotExist:
                pass
        form = self.get_form()
        form.is_valid()
        kwargs['children'] = [reg.child for reg in form.cleaned_data.get('registrations', [])]
        return super(TransportMoveView, self).get_context_data(**kwargs)
