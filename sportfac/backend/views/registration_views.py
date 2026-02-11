import collections
import logging
from datetime import datetime
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import IntegrityError
from django.db import connection
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import View
from formtools.wizard.views import SessionWizardView

from absences.models import Absence
from activities.models import Activity
from activities.models import Course
from activities.models import ExtraNeed
from backend.forms import BillingForm
from backend.forms import ChildSelectForm
from backend.forms import CourseSelectForm
from backend.forms import ExtraInfoFormSet
from backend.forms import RegistrationForm
from backend.forms import SendConfirmationForm
from profiles.models import FamilyUser as User
from registrations.forms import BillExportForm
from registrations.forms import BillForm
from registrations.forms import MoveRegistrationsForm
from registrations.forms import MoveTransportForm
from registrations.forms import TransportForm
from registrations.models import Bill
from registrations.models import ExtraInfo
from registrations.models import Registration
from registrations.models import Transport
from registrations.resources import BillResource
from registrations.resources import RegistrationResource
from registrations.resources import enhance_invoices_xls
from registrations.views.utils import BillMixin
from registrations.views.utils import PaymentMixin

from .mixins import BackendMixin
from .mixins import ExcelResponseMixin
from .mixins import FullBackendMixin


logger = logging.getLogger(__name__)


class RegistrationMixin(BackendMixin):
    def get_queryset_source(self):
        return super().get_queryset()

    def get_queryset(self):
        user: User = self.request.user
        queryset = self.get_queryset_source()
        if user.is_full_manager:
            return queryset
        return queryset.filter(course__activity__in=user.managed_activities.all())


class RegistrationDetailView(RegistrationMixin, DetailView):
    model = Registration
    template_name = "backend/registration/detail.html"


class RegistrationExportView(RegistrationMixin, ExcelResponseMixin, View):
    filename = _("registrations")

    def get_resource(self):
        return RegistrationResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class RegistrationListView(RegistrationMixin, ListView):
    model = Registration
    template_name = "backend/registration/list.html"

    def get_queryset_source(self):
        return Registration.all_objects.all()

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("course", "child", "child__family")
            .prefetch_related("course__activity")
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        destination_course = form.cleaned_data["destination"]
        destination_children = {registration.child for registration in destination_course.participants.all()}
        if "success_url" in form.data:
            redirect = form.data["success_url"]
        else:
            redirect = form.cleaned_data["registrations"].first().course.backend_url
        previous_courses = set()
        with transaction.atomic():
            for registration in form.cleaned_data["registrations"]:
                if registration.course == destination_course:
                    # The child is not moving, let's just confirm the registration
                    registration.set_confirmed()
                    registration.save()
                    continue

                # from this point, we know that previous registration has to be canceled one way or another
                previous_courses.add(registration.course)
                if registration.child in destination_children:
                    # Child is already registered to destination course, we just need to remove him from previous course
                    registration.cancel(reason=Registration.REASON.moved, user=self.request.user)
                    registration.save()
                    continue
                # the child is moving to a new course, and leaving the previous one
                registration.delete_future_absences()
                registration.course = destination_course
                registration.set_confirmed()
                registration.save()
                registration.create_future_absences()

        for course in previous_courses:
            # Trigger the calculation of #participants
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

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step == _("Course"):
            kwargs.update({"user": self.request.user})
        return kwargs


class RegistrationDeleteView(RegistrationMixin, DeleteView):
    model = Registration
    template_name = "backend/registration/confirm_delete.html"

    def get_success_url(self):
        return self.object.course.get_backend_url()

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.cancel(reason=Registration.REASON.admin, user=self.request.user)
            self.object.save()
        except IntegrityError:
            # The registration for child and course existed previously and
            # was already canceled. We do not need to cancel it again
            self.object.delete()
        messages.success(self.request, _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)


class RegistrationUpdateView(SuccessMessageMixin, RegistrationMixin, UpdateView):
    model = Registration
    form_class = RegistrationForm
    template_name = "backend/registration/update.html"
    success_message = _("Registration has been updated.")
    success_url = reverse_lazy("backend:registration-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

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
                self.object.refresh_from_db()
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
        initial_status = self.get_object().status

        if settings.KEPCHUP_USE_ABSENCES and form.cleaned_data["course"] != initial_course:
            # as we are changing course, remove the future absences
            self.object.delete_future_absences()

        # This will trigger the creation of future absences for the new course
        self.object = form.save()
        if self.object.course != initial_course:
            # the course has changed, we need to update the number of participants
            initial_course.save()
        extrainfo_form.instance = self.object
        extrainfo_form.save()

        if initial_status != self.object.status:
            if self.object.is_confirmed or self.object.is_validated:
                # Send the conformation message
                self.object.set_confirmed()
            elif self.object.is_canceled:
                # Cancel and remove future absences
                self.object.cancel(reason=Registration.REASON.admin, user=self.request.user)

        # Create invoice if necessary
        if self.object.is_confirmed and not self.object.paid and not self.object.bill:
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
        registration_qs = Registration.objects.filter(status=Registration.STATUS.waiting)
        user: User = self.request.user
        if user.is_restricted_manager:
            registration_qs = registration_qs.filter(course__activity__in=user.managed_activities.all())
        context["registrations"] = registration_qs
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


class BillListView(FullBackendMixin, ListView):
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
            Bill.objects.exclude(status=Bill.STATUS.just_created)
            .filter(created__gte=start, created__lte=end)
            .select_related("family")
            .order_by("status", "billing_identifier")
        )

    def _apply_filters(self, qs, cleaned_data):
        """
        Applies filters to the queryset based on form data.
        """
        start = cleaned_data["start"]
        end = cleaned_data["end"]
        status = cleaned_data["status"]
        amount = cleaned_data["amount"]

        if start and end:
            qs = qs.filter(created__gte=start, created__lte=end)

        if status and status != "all":
            qs = qs.filter(status=Bill.STATUS.paid if status == "paid" else Bill.STATUS.waiting)

        if amount and amount != "all":
            qs = qs.exclude(total=0) if amount == "positive" else qs.filter(total=0)

        return qs.prefetch_related("registrations__child")

    def _apply_sorting(self, qs, sorting):
        """
        Applies sorting to the queryset based on the sorting data from the form.
        """
        if not sorting:
            return qs

        # Mapping DataTables indices to model fields
        column_mapping = {
            0: "billing_identifier",
            1: "created",
            2: "user__username",
            3: "total",
            4: "status",
        }

        sorting_fields = []
        for sort in sorting.split(","):
            index, direction = sort.split(":")
            field = column_mapping.get(int(index))
            if field:
                sorting_fields.append(f"-{field}" if direction == "desc" else field)

        return qs.order_by(*sorting_fields) if sorting_fields else qs

    def _get_filename(self, start, end):
        """
        Generates a filename for the exported file.
        """
        if start and end:
            return _("invoices-{}-{}.xlsx".format(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")))
        return _("invoices.xlsx")

    def _generate_export_response(self, qs, filename):
        """
        Generates an export response with the given queryset and filename.
        """
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        resource = BillResource()
        export = resource.export(qs)

        rendered_xlsx = BytesIO(export.xlsx)
        enhanced_xlsx = enhance_invoices_xls(rendered_xlsx)
        response = HttpResponse(enhanced_xlsx, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def post(self, request, *args, **kwargs):
        form = BillExportForm(request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form))

        # Extract form data
        cleaned_data = form.cleaned_data
        qs = self._apply_filters(self.get_queryset(), cleaned_data)
        qs = self._apply_sorting(qs, cleaned_data.get("sorting"))
        filename = self._get_filename(cleaned_data.get("start"), cleaned_data.get("end"))
        return self._generate_export_response(qs, filename)


class BillExportView(FullBackendMixin, ExcelResponseMixin, View):
    filename = _("invoices")

    def get_resource(self):
        return BillResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class BillDetailView(FullBackendMixin, BillMixin, PaymentMixin, DetailView):
    """
    Display the bill: admin view
    """

    context_object_name = "invoice"
    model = Bill
    template_name = "backend/registration/invoice-detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object
        context["registrations"] = invoice.registrations.all()
        for reg in context["registrations"]:
            reg.row_span = 1 + reg.extra_infos.count()
        context["rentals"] = invoice.rentals.all()
        context["total_amount"] = invoice.total
        return context


class BillUpdateView(SuccessMessageMixin, FullBackendMixin, UpdateView):
    model = Bill
    form_class = BillForm
    template_name = "backend/registration/bill-update.html"
    success_message = _("Bill has been updated.")
    success_url = reverse_lazy("backend:bill-list")

    def form_valid(self, form):
        self.object: Bill = form.save(commit=False)
        old_status = self.get_object().status
        new_status = self.object.status
        # Cascade only if status changed → paid
        if old_status != Bill.STATUS.paid and new_status == Bill.STATUS.paid:
            self.object.close()

        self.object.save(force_status=True)
        return super().form_valid(form)


class TransportListView(FullBackendMixin, ListView):
    model = Transport
    template_name = "backend/registration/transport-list.html"


class TransportDetailView(FullBackendMixin, DetailView):
    model = Transport
    template_name = "backend/registration/transport-detail.html"
    queryset = Transport.objects.prefetch_related(
        "participants",
        "participants__child",
        "participants__course",
        "participants__child__absences",
    )

    def get_context_data(self, **kwargs):
        children = {registration.child for registration in self.object.participants.all()}
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            courses = {
                absence.session.course
                for child in children
                for absence in child.absences.select_related("session__course", "session__course__activity")
            }
        else:
            courses = {registration.course for registration in self.object.participants.all()}

        try:
            # FIXME: this is a despicable hack where I hope the question name is 'Arrêt...'
            questions = ExtraNeed.objects.filter(question_label__startswith="Arr")
            all_extras = {
                extra.registration.child: extra.value
                for extra in ExtraInfo.objects.exclude(registration__status=Registration.STATUS.canceled).filter(
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
        kwargs["all_dates"].sort(reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC)

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


class TransportCreateView(SuccessMessageMixin, FullBackendMixin, CreateView):
    model = Transport
    form_class = TransportForm
    template_name = "backend/registration/transport-create.html"
    success_url = reverse_lazy("backend:transport-list")
    success_message = _("Transport has been created.")


class TransportUpdateView(SuccessMessageMixin, FullBackendMixin, UpdateView):
    model = Transport
    form_class = TransportForm
    template_name = "backend/registration/transport-update.html"
    success_message = _("Transport has been updated.")
    success_url = reverse_lazy("backend:transport-list")


class TransportDeleteView(SuccessMessageMixin, FullBackendMixin, DeleteView):
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
