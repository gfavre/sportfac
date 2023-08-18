import collections
import logging
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError, connection, transaction
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView, View

from absences.models import Absence
from activities.models import Activity, Course, ExtraNeed
from backend.forms import (
    BillingForm,
    ChildSelectForm,
    CourseSelectForm,
    ExtraInfoFormSet,
    RegistrationForm,
    SendConfirmationForm,
)
from formtools.wizard.views import SessionWizardView
from registrations.forms import BillExportForm, BillForm, MoveRegistrationsForm, MoveTransportForm, TransportForm
from registrations.models import Bill, ExtraInfo, Registration, Transport
from registrations.resources import BillResource, RegistrationResource
from registrations.views import BillMixin, PaymentMixin

from .mixins import BackendMixin, ExcelResponseMixin


logger = logging.getLogger(__name__)


class RegistrationDetailView(BackendMixin, DetailView):
    model = Registration
    template_name = "backend/registration/detail.html"


class RegistrationExportView(BackendMixin, ExcelResponseMixin, View):
    filename = _("registrations")

    def get_resource(self):
        return RegistrationResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class RegistrationListView(BackendMixin, ListView):
    model = Registration
    template_name = "backend/registration/list.html"

    def get_queryset(self):
        return Registration.objects.select_related("course", "child", "child__family").prefetch_related(
            "course__activity"
        )


class RegistrationsMoveView(BackendMixin, FormView):
    form_class = MoveRegistrationsForm
    template_name = "backend/registration/move.html"

    def get_initial(self):
        initial = super().get_initial()
        if "course" in self.request.GET:
            try:
                prev_course_id = int(self.request.GET.get("course"))
                initial["origin_course_id"] = Course.objects.get(pk=prev_course_id).pk
            except (IndexError, TypeError, Course.DoesNotExist):
                pass
        elif "activity" in self.request.GET:
            try:
                prev_activity_id = int(self.request.GET.get("activity"))
                initial["origin_activity_id"] = Activity.objects.get(pk=prev_activity_id).pk
            except (IndexError, TypeError, Activity.DoesNotExist):
                pass
        return initial

    def form_valid(self, form):
        course = form.cleaned_data["destination"]
        if "success_url" in form.data:
            redirect = form.data["success_url"]
        else:
            redirect = form.cleaned_data["registrations"].first().course.backend_url
        previous_courses = set()
        with transaction.atomic():
            for registration in form.cleaned_data["registrations"]:
                if registration.course != course:
                    registration.delete_future_absences()
                    previous_courses.add(registration.course)
                registration.course = course
                registration.set_confirmed()
                registration.save()
                registration.create_future_absences()
        for course in previous_courses:
            course.save()
        message = _("Registrations of %(nb)s children have been moved.")
        message %= {"nb": form.cleaned_data["registrations"].count()}
        messages.add_message(self.request, messages.SUCCESS, message)
        return HttpResponseRedirect(redirect)

    def get_context_data(self, **kwargs):
        form = self.get_form()
        form.is_valid()

        if "activity" in self.request.GET:
            try:
                prev_activity_id = int(self.request.GET.get("activity"))
                kwargs["success_url"] = Activity.objects.get(pk=prev_activity_id).backend_absences_url
            except (IndexError, TypeError, Activity.DoesNotExist):
                pass
        elif "course" in self.request.GET:
            try:
                prev_course_id = int(self.request.GET.get("course"))
                kwargs["success_url"] = Course.objects.get(pk=prev_course_id).backend_absences_url
            except (IndexError, TypeError, Course.DoesNotExist):
                pass
        if hasattr(form, "cleaned_data"):
            kwargs["children"] = [reg.child for reg in form.cleaned_data.get("registrations", [])]

        return super().get_context_data(**kwargs)


class RegistrationCreateView(BackendMixin, SessionWizardView):
    form_list = (
        (_("Child"), ChildSelectForm),
        (_("Course"), CourseSelectForm),
        (_("Email"), SendConfirmationForm),
        (_("Billing"), BillingForm),
    )
    condition_dict = {
        _("Billing"): not settings.KEPCHUP_NO_PAYMENT,
        _("Email"): settings.KEPCHUP_NO_PAYMENT,
    }
    template_name = "backend/registration/wizard.html"
    instance = None

    def set_message(self, level=messages.INFO, message=""):
        messages.add_message(self.request, level, message)

    @transaction.atomic
    def done(self, form_list, form_dict, **kwargs):
        # form_list
        # [<ChildSelectForm bound=True, valid=True, fields=(child)>,
        # <CourseSelectForm bound=True, valid=True, fields=(course)>,
        # <BillingForm bound=True, valid=True, fields=(paid;send_confirmation)>]
        user = self.instance.child.family
        message = _("Registration for %(child)s to %(course)s has been validated.")
        message %= {"child": self.instance.child, "course": self.instance.course.short_name}
        send_confirmation = form_list[-1].cleaned_data.get("send_confirmation", False)
        self.set_message(messages.SUCCESS, message)
        response = HttpResponseRedirect(self.instance.course.get_backend_url())
        if settings.KEPCHUP_NO_PAYMENT:
            self.instance.set_confirmed(send_confirmation=send_confirmation)
            self.instance.save()
            return response
        try:
            self.instance.price = self.instance.get_price()
            status = Bill.STATUS.paid
            if not self.instance.paid:
                status = Bill.STATUS.waiting
                if self.instance.get_price() == 0:
                    status = Bill.STATUS.paid
            bill = Bill.objects.create(status=status, family=user)
            if send_confirmation:
                bill.send_confirmation()
            self.instance.bill = bill
            message = _('The bill %(identifier)s has been created. <a href="%(url)s">Please review it.</a>')
            message = mark_safe(message % {"identifier": bill.billing_identifier, "url": bill.backend_url})
            self.set_message(messages.INFO, message)
            self.instance.set_confirmed()
            self.instance.save()
            bill.send_to_accountant()
        except IntegrityError:
            message = _("A registration for %(child)s to %(course)s already exists.")
            message %= {"child": self.instance.child, "course": self.instance.course.short_name}
            self.set_message(messages.WARNING, message)
        return response

    def get_form_instance(self, step):
        if self.instance is None:
            self.instance = Registration()
        return self.instance


class RegistrationDeleteView(BackendMixin, DeleteView):
    model = Registration
    template_name = "backend/registration/confirm_delete.html"

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
        messages.success(self.request, _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)


class RegistrationUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Registration
    form_class = RegistrationForm
    template_name = "backend/registration/update.html"
    success_message = _("Registration has been updated.")
    success_url = reverse_lazy("backend:registration-list")

    def get_success_url(self):
        course = self.request.GET.get("course", None)
        if not course:
            return self.success_url
        course_obj = get_object_or_404(Course, pk=course)
        return course_obj.get_backend_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        extras = {}
        courses = Course.objects.prefetch_related("extra").annotate(nb_extra=Count("extra"))
        for course in courses.exclude(nb_extra=0):
            extras[course.id] = course.extra.all()
        context["extra_questions"] = extras
        context["need_extra"] = self.object.course.id in extras
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
        initial_course = self.get_object().course
        self.object = form.save()
        if self.object.course != initial_course:
            # this will trigger the calculation of #participants
            initial_course.save()
            if settings.KEPCHUP_USE_ABSENCES:
                self.object.delete_future_absences()

        extrainfo_form.instance = self.object
        extrainfo_form.save()

        if self.object.status in (Registration.STATUS.confirmed, Registration.STATUS.valid):
            self.object.set_confirmed()
        elif self.object.status == Registration.STATUS.canceled:
            self.object.cancel()
        if self.object.status == Registration.STATUS.confirmed and not self.object.paid and not self.object.bill:
            status = Bill.STATUS.waiting
            if self.object.get_price() == 0:
                status = Bill.STATUS.paid
            bill = Bill.objects.create(
                status=status,
                family=self.object.child.family,
            )
            self.object.bill = bill
            self.object.save()
            bill.save()

        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, extrainfo_form):
        return self.render_to_response(self.get_context_data(form=form, extrainfo_form=extrainfo_form))


class RegistrationValidateView(BackendMixin, TemplateView):
    template_name = "backend/registration/confirm_validate.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registrations"] = Registration.objects.filter(status=Registration.STATUS.waiting)
        return context

    def post(self, request, *args, **kwargs):
        to_update = Registration.objects.filter(status=Registration.STATUS.waiting).select_related("child__family")
        families = {registration.child.family for registration in to_update}
        count = to_update.count()
        to_update.update(status=Registration.STATUS.confirmed)
        messages.success(request, _("%d registrations have been confirmed") % count)
        from registrations.tasks import send_confirmation as send_confirmation_task

        for family in families:
            try:
                tenant_pk = connection.tenant.pk
            except AttributeError:
                tenant_pk = None
            transaction.on_commit(
                lambda: send_confirmation_task.delay(
                    user_pk=str(family.pk),  # noqa: B023
                    tenant_pk=tenant_pk,  # noqa: B023
                    language=get_language(),
                )
            )
        return HttpResponseRedirect(reverse_lazy("backend:registration-list"))


class BillListView(BackendMixin, ListView):
    model = Bill
    template_name = "backend/registration/bill-list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["start"], context["end"] = self.get_start_end()
        if "form" not in kwargs:
            context["form"] = BillExportForm()
        return context

    def get_start_end(self):
        bill = Bill.objects.order_by("created").first()
        if bill:
            start = Bill.objects.order_by("created").first().created
        else:
            start = now()
        end = now()
        if "start" in self.request.GET:
            try:
                start = datetime.strptime(self.request.GET.get("start"), "%Y-%m-%d").date()
            except ValueError:
                pass
        if "end" in self.request.GET:
            try:
                end = datetime.strptime(self.request.GET.get("end"), "%Y-%m-%d").date()
            except ValueError:
                pass
        return start, end

    def get_queryset(self):
        start, end = self.get_start_end()
        return (
            Bill.objects.filter(created__gte=start, created__lte=end)
            .select_related("family")
            .order_by("status", "billing_identifier")
        )

    def post(self, request, *args, **kwargs):
        start, end = self.get_start_end()
        form = BillExportForm(request.POST)
        if form.is_valid():
            qs = self.get_queryset().prefetch_related("registrations__child")
            if not form.cleaned_data.get("include_0_bills"):
                qs = qs.exclude(total=0)

            filename = _("invoices-{}-{}.xlsx".format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            resource = BillResource()
            export = resource.export(qs)
            response = HttpResponse(content_type=content_type)
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response.write(export.xlsx)
            return response
        return self.render_to_response(self.get_context_data(form=form))


class BillDetailView(BackendMixin, BillMixin, PaymentMixin, DetailView):
    model = Bill
    template_name = "backend/registration/bill-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object.is_paid:
            return context
        context["transaction"] = self.get_transaction(self.object)
        return context


class BillUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Bill
    form_class = BillForm
    template_name = "backend/registration/bill-update.html"
    success_message = _("Bill has been updated.")
    success_url = reverse_lazy("backend:bill-list")

    def form_valid(self, form):
        self.object = self.get_object()
        if form.cleaned_data["status"] == Bill.STATUS.paid:
            self.object.close()
        else:
            self.object.status = form.cleaned_data["status"]
        self.object.save(force_status=True)
        return HttpResponseRedirect(self.get_success_url())


class TransportListView(BackendMixin, ListView):
    model = Transport
    template_name = "backend/registration/transport-list.html"


class TransportDetailView(BackendMixin, DetailView):
    model = Transport
    template_name = "backend/registration/transport-detail.html"
    queryset = Transport.objects.prefetch_related(
        "participants",
        "participants__child",
        "participants__course",
        "participants__child__absence_set",
    )

    def get_context_data(self, **kwargs):
        children = {registration.child for registration in self.object.participants.all()}
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            courses = {
                absence.session.course
                for child in children
                for absence in child.absence_set.select_related("session__course", "session__course__activity")
            }
        else:
            courses = {registration.course for registration in self.object.participants.all()}

        try:
            questions = ExtraNeed.objects.filter(question_label__startswith="Arr")
            all_extras = {
                extra.registration.child: extra.value
                for extra in ExtraInfo.objects.filter(
                    registration__child__in=children,
                    registration__course__in=courses,
                    key__in=questions,
                )
            }
        except ExtraNeed.DoesNotExist:
            all_extras = {}
        Participant = collections.namedtuple(
            "Participant", ["registration", "child", "latest_course", "child_stop", "all_absences"]
        )
        participants_list = []

        qs = (
            Absence.objects.filter(child__in=children, session__course__in=courses)
            .select_related("session", "child", "session__course", "session__course__activity")
            .order_by("session__date", "child__last_name", "child__first_name")
        )

        all_dates = set(qs.values_list("session__date", flat=True))
        kwargs["all_dates"] = list(all_dates)
        kwargs["all_dates"].sort(reverse=True)

        for registration in self.object.participants.all():
            child_absences = {absence.session.date: absence for absence in qs if absence.child == registration.child}
            absences = [child_absences.get(session_date, None) for session_date in kwargs["all_dates"]]
            participant = Participant(
                registration=registration,
                child=registration.child,
                latest_course=registration.course,
                child_stop=all_extras.get(registration.child, ""),
                all_absences=absences,
            )
            participants_list.append(participant)
        kwargs["participants_list"] = list(participants_list)

        return super().get_context_data(**kwargs)


class TransportCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = Transport
    form_class = TransportForm
    template_name = "backend/registration/transport-create.html"
    success_url = reverse_lazy("backend:transport-list")
    success_message = _("Transport has been created.")


class TransportUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = Transport
    form_class = TransportForm
    template_name = "backend/registration/transport-update.html"
    success_message = _("Transport has been updated.")
    success_url = reverse_lazy("backend:transport-list")


class TransportDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = Transport
    template_name = "backend/registration/transport_confirm_delete.html"
    success_url = reverse_lazy("backend:transport-list")
    success_message = _("Transport has been deleted.")


class TransportMoveView(BackendMixin, FormView):
    form_class = MoveTransportForm
    template_name = "backend/registration/move.html"

    def form_valid(self, form):
        transport = form.cleaned_data["destination"]
        for registration in form.cleaned_data["registrations"]:
            registration.transport = transport
            registration.set_confirmed()
            registration.save()
        message = _("Registrations of %(nb)s children have been moved.")
        message %= {"nb": form.cleaned_data["registrations"].count()}
        messages.add_message(self.request, messages.SUCCESS, message)
        return HttpResponseRedirect(transport.backend_url)

    def get_context_data(self, **kwargs):
        try:
            prev = int(self.request.GET.get("prev"))
        except (IndexError, TypeError):
            prev = None
        kwargs["origin"] = None
        if prev:
            try:
                kwargs["origin"] = Transport.objects.get(pk=prev)
            except Transport.DoesNotExist:
                pass
        form = self.get_form()
        form.is_valid()
        kwargs["children"] = [reg.child for reg in form.cleaned_data.get("registrations", [])]
        return super().get_context_data(**kwargs)


def show_extra_questions(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step(_("Course")) or {}
    course = cleaned_data.get("course")
    if course and course.extra.count():
        return True
    return False
