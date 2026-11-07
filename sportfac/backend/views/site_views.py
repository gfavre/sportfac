# from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.flatpages.models import FlatPage
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import BooleanField
from django.db.models import Case
from django.db.models import Count
from django.db.models import Prefetch
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView
from django.views.generic import View

from appointments.forms import AppointmentCreateForm
from appointments.forms import AppointmentForm
from appointments.models import Appointment
from appointments.models import AppointmentSlot
from appointments.models import Rental
from appointments.resources import AppointmentResource
from backend.dynamic_preferences_registry import global_preferences_registry
from mailer.forms import GenericEmailForm
from mailer.models import GenericEmail
from registrations.models import Child
from wizard.forms import WizardStepForm
from wizard.models import WizardStep

from ..forms import FlatPageForm
from .mixins import ExcelResponseMixin
from .mixins import FullBackendMixin


class AppointmentsManagementView(FullBackendMixin, TemplateView):
    template_name = "appointments/backend/create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if AppointmentSlot.objects.exists():
            context["start"] = AppointmentSlot.objects.first().start.date().isoformat()
        else:
            context["start"] = now().date().isoformat()
        return context


class AppointmentsListView(FullBackendMixin, ListView):
    model = AppointmentSlot
    template_name = "appointments/backend/list.html"
    paginate_by = 25

    def get_queryset(self):
        self.include_empty = self.request.GET.get("empty", "1") != "0"
        self.search = self.request.GET.get("q", "").strip()
        self.available_days = list(
            AppointmentSlot.objects.annotate(day=TruncDate("start"))
            .values("day")
            .annotate(bookings=Count("appointments"))
            .order_by("day")
        )
        selected = self.request.GET.get("date", "all")
        try:
            selected_date = parse_date(selected) if selected != "all" else None
        except ValueError:
            selected_date = None
        self.selected_date = selected_date.isoformat() if selected_date else "all"
        slots = super().get_queryset().order_by("start", "end", "pk")
        if selected_date:
            slots = slots.filter(start__date=selected_date)
        if not self.include_empty:
            slots = slots.filter(appointments__isnull=False).distinct()
        appointments = Appointment.objects.select_related("child__family")
        if self.search:
            matches = Appointment.objects.all()
            for term in self.search.split():
                matches = matches.filter(
                    Q(child__first_name__icontains=term)
                    | Q(child__last_name__icontains=term)
                    | Q(child__family__email__icontains=term)
                    | Q(email__icontains=term)
                )
            slots = slots.filter(pk__in=matches.values("slot_id"))
            appointments = appointments.annotate(
                search_match=Case(
                    When(pk__in=matches.values("pk"), then=Value(True)),
                    default=Value(False),
                    output_field=BooleanField(),
                )
            ).order_by("-search_match", "child__last_name", "child__first_name", "pk")
        self.summary = slots.aggregate(
            slot_count=Count("pk", distinct=True), appointment_count=Count("appointments", distinct=True)
        )
        return slots.prefetch_related(Prefetch("appointments", queryset=appointments))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.summary)
        context["available_days"] = self.available_days
        context["selected_date"] = self.selected_date
        context["include_empty"] = self.include_empty
        context["search"] = self.search
        context["page_query"] = urlencode(
            {"date": self.selected_date, "empty": int(self.include_empty), "q": self.search}
        )
        return context


class AppointmentCreateView(SuccessMessageMixin, FullBackendMixin, CreateView):
    model = Appointment
    form_class = AppointmentCreateForm
    template_name = "appointments/backend/book.html"
    success_url = reverse_lazy("backend:appointments-list")
    success_message = _("Le rendez-vous a été ajouté.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["search"] = self.request.GET.get("q", "").strip()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search"] = self.request.GET.get("q", "").strip()
        context["single_child"] = context["form"].single_child
        return context

    @transaction.atomic
    def form_valid(self, form):
        child = Child.objects.select_for_update().get(pk=form.cleaned_data["child"].pk)
        slot = AppointmentSlot.objects.select_for_update().get(pk=form.cleaned_data["slot"].pk)
        if slot.start < now() or slot.appointments.count() >= slot.places:
            form.add_error("slot", _("Ce créneau est complet ou passé. Choisissez un autre horaire."))
            return self.form_invalid(form)
        if Appointment.objects.filter(child=child, slot=slot).exists():
            form.add_error("slot", _("Cet enfant a déjà un rendez-vous sur ce créneau."))
            return self.form_invalid(form)
        rental = Rental.objects.select_for_update().filter(child=child).first()
        rental_field = {"pickup": "pickup_appointment", "return": "return_appointment"}.get(slot.appointment_type)
        if rental_field and rental and getattr(rental, f"{rental_field}_id"):
            form.add_error("slot", _("Cet enfant a déjà ce type de rendez-vous. Modifiez le rendez-vous existant."))
            return self.form_invalid(form)
        if rental_field and not rental:
            rental = Rental.objects.create(
                child=child, amount=global_preferences_registry.manager()["site__RENTAL_PRICE"]
            )
        response = super().form_valid(form)
        if rental_field:
            setattr(rental, rental_field, self.object)
            rental.save(update_fields=[rental_field, "modified"])
        return response  # noqa: R504 - the rental link must be saved after the appointment.


class AppointmentModalMixin:
    def get_template_names(self):
        if self.request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return [self.modal_template_name]
        return super().get_template_names()

    def is_modal_request(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def mutation_response(self, response, **data):
        if self.is_modal_request():
            return JsonResponse({"success": True, **data})
        return response


class AppointmentUpdateView(AppointmentModalMixin, SuccessMessageMixin, FullBackendMixin, UpdateView):
    form_class = AppointmentForm
    model = Appointment
    pk_url_kwarg = "appointment"
    success_url = reverse_lazy("backend:appointments-list")
    success_message = _("Appointment has been updated.")
    template_name = "appointments/backend/update.html"
    modal_template_name = "appointments/backend/edit_modal.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.is_modal_request():
            form.helper.label_class = ""
            form.helper.field_class = ""
            form.fields["slot"].label = _("Créneau de rendez-vous")
        return form

    def get_object(self, queryset=None):
        appointment = super().get_object(queryset)
        self.current_slot = appointment.slot
        return appointment

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_slot"] = self.current_slot
        return context

    @transaction.atomic
    def form_valid(self, form):
        slot = AppointmentSlot.objects.select_for_update().get(pk=form.cleaned_data["slot"].pk)
        if slot.pk != Appointment.objects.get(pk=self.object.pk).slot_id and slot.appointments.count() >= slot.places:
            form.add_error("slot", _("Ce créneau est complet. Choisissez un autre horaire."))
            return self.form_invalid(form)
        return self.mutation_response(super().form_valid(form))


class AppointmentDeleteView(AppointmentModalMixin, SuccessMessageMixin, FullBackendMixin, DeleteView):
    model = Appointment
    template_name = "appointments/backend/confirm_delete.html"
    success_url = reverse_lazy("backend:appointments-list")
    success_message = _("Appointment has been canceled.")
    pk_url_kwarg = "appointment"
    modal_template_name = "appointments/backend/delete_modal.html"

    def delete(self, request, *args, **kwargs):
        return self.mutation_response(super().delete(request, *args, **kwargs), deleted=True)


class AppointmentsExportView(FullBackendMixin, ExcelResponseMixin, View):
    filename = _("appointments")

    def get_resource(self):
        return AppointmentResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class FlatPageListView(FullBackendMixin, ListView):
    model = FlatPage
    template_name = "backend/site/flatpage_list.html"


class FlatPageUpdateView(SuccessMessageMixin, FullBackendMixin, UpdateView):
    model = FlatPage
    form_class = FlatPageForm
    template_name = "backend/site/flatpage_update.html"
    success_url = reverse_lazy("backend:flatpages-list")
    success_message = _('<a href="%(url)s" class="alert-link">Page "%(title)s"</a> has been updated.')

    def get_success_message(self, cleaned_data):
        return mark_safe(self.success_message % {"url": self.object.url, "title": cleaned_data.get("title")})


class GenericEmailListView(FullBackendMixin, ListView):
    model = GenericEmail
    template_name = "backend/mail/emails_list.html"


class GenericEmailUpdateView(SuccessMessageMixin, FullBackendMixin, UpdateView):
    model = GenericEmail
    form_class = GenericEmailForm
    template_name = "backend/mail/emails_update.html"
    success_url = reverse_lazy("backend:emails-list")
    success_message = _("Generic email has been saved")

    def form_valid(self, form):
        subject_heading = form.get_tmpl_heading(self.object.subject_template.content)
        subject_body = form.cleanup_tmpl(form.cleaned_data["subject_text"])
        self.object.subject_template.content = subject_heading + subject_body
        self.object.subject_template.save()

        message_heading = form.get_tmpl_heading(self.object.body_template.content)
        message_body = form.cleanup_tmpl(form.cleaned_data["body_text"])
        if message_heading:
            self.object.body_template.content = message_heading + "\n" + message_body
        else:
            self.object.body_template.content = message_body
        self.object.body_template.save()
        return super().form_valid(form)


class WizardStepListView(FullBackendMixin, ListView):
    model = WizardStep
    template_name = "backend/wizard/step_list.html"

    def get_queryset(self):
        return super().get_queryset().filter(editable_in_backend=True)


class WizardStepUpdateView(FullBackendMixin, UpdateView):
    model = WizardStep
    form_class = WizardStepForm
    template_name = "backend/wizard/step_update.html"
    success_url = reverse_lazy("backend:wizard-steps")
