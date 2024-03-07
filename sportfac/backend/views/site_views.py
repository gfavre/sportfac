from datetime import timedelta

from django.contrib.flatpages.models import FlatPage
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, ListView, TemplateView, UpdateView, View

from appointments.models import Appointment, AppointmentSlot
from appointments.resources import AppointmentResource
from mailer.forms import GenericEmailForm
from mailer.models import GenericEmail

from ..forms import FlatPageForm
from .mixins import ExcelResponseMixin, FullBackendMixin


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

    def get_queryset(self):
        min_date = now() - timedelta(hours=4)
        return AppointmentSlot.objects.filter(start__gte=min_date).prefetch_related(
            "appointments", "appointments__child"
        )


class AppointmentDeleteView(SuccessMessageMixin, FullBackendMixin, DeleteView):
    model = Appointment
    template_name = "appointments/backend/confirm_delete.html"
    success_url = reverse_lazy("backend:appointments-list")
    success_message = _("Appointment has been canceled.")
    pk_url_kwarg = "appointment"


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
