from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.sessions.models import Session
from django.db import connection, transaction
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, FormView, ListView, UpdateView

from ..forms import YearCreateForm, YearForm, YearSelectForm
from ..models import Domain, YearTenant
from ..tasks import create_tenant
from .mixins import BackendMixin, KepchupStaffMixin


class ChangeYearFormView(SuccessMessageMixin, KepchupStaffMixin, FormView):
    form_class = YearSelectForm
    template_name = "backend/year/change.html"

    def get_success_url(self):
        if not url_has_allowed_host_and_scheme(url=self.success_url, allowed_hosts=[self.request.get_host()]):
            return reverse("backend:home")
        return self.success_url

    def form_valid(self, form):
        self.success_url = form.cleaned_data["next"]
        response = super().form_valid(form)
        tenant = form.cleaned_data["tenant"]
        self.request.session[settings.VERSION_SESSION_NAME] = tenant.domains.first().domain
        return response  # noqa: R504

    def get_success_message(self, cleaned_data):
        tenant = cleaned_data["tenant"]
        message = _("You are now editing %s") % tenant
        if tenant.is_production:
            message = _("You are now editing period currently in production")
        elif tenant.is_past:
            message = _("You are now reviewing %s") % tenant
        elif tenant.is_future:
            message = _("You are now previewing %s") % tenant
        return mark_safe(message)


class ChangeProductionYearFormView(SuccessMessageMixin, BackendMixin, FormView):
    form_class = YearSelectForm
    template_name = "backend/year/change_production.html"

    def get(self, request, *args, **kwargs):
        return redirect("backend:year-list")

    def get_success_url(self):
        if not url_has_allowed_host_and_scheme(url=self.success_url, allowed_hosts=[self.request.get_host()]):
            return reverse("backend:home")
        return self.success_url

    @transaction.atomic
    def form_valid(self, form):
        self.success_url = form.cleaned_data["next"]
        tenant = form.cleaned_data["tenant"]
        response = super().form_valid(form)
        current_domain = Domain.objects.filter(is_current=True).first()
        current_domain.is_current = False
        current_domain.save()
        new_domain = tenant.domains.first()
        new_domain.is_current = True
        new_domain.save()
        # log every one out
        Session.objects.exclude(session_key=self.request.session.session_key).delete()
        self.request.session[settings.VERSION_SESSION_NAME] = new_domain.domain

        connection.set_tenant(tenant)
        return response  # noqa: R504

    def get_success_message(self, cleaned_data):
        now = timezone.now()
        tenant = cleaned_data["tenant"]
        possible_new_tenants = (
            YearTenant.objects.exclude(domains__in=tenant.domains.all())
            .filter(start_date__lte=now, end_date__gte=now, status=YearTenant.STATUS.ready)
            .order_by("start_date", "end_date")
        )

        if tenant.is_future and possible_new_tenants.count():
            message = _(
                "The period has been changed. However, it is in the future. "
                "It will be automatically switched back tonight"
            )
        elif tenant.is_past and possible_new_tenants.count():
            message = _(
                "The period has been changed. However, it is in the past. "
                "It will be automatically switched back tonight"
            )
        else:
            message = _("The period has been changed.")
        return mark_safe(message)


class YearListView(BackendMixin, ListView):
    model = YearTenant
    template_name = "backend/year/list.html"


class YearUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = YearTenant
    form_class = YearForm
    success_url = reverse_lazy("backend:year-list")
    success_message = _("Period has been updated.")
    template_name = "backend/year/update.html"

    def post(self, request, *args, **kwargs):
        connection.set_schema_to_public()
        return super().post(request, *args, **kwargs)


class YearDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = YearTenant
    success_message = _("Period has been deleted.")
    success_url = reverse_lazy("backend:year-list")
    template_name = "backend/year/confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = str(self.get_object())
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Period %(identifier)s has been deleted.") % {"identifier": identifier},
        )
        connection.set_schema_to_public()
        return super().delete(request, *args, **kwargs)


class YearCreateView(SuccessMessageMixin, BackendMixin, FormView):
    form_class = YearCreateForm
    success_url = reverse_lazy("backend:year-list")
    template_name = "backend/year/create.html"
    success_message = _("A new period, starting on %s and ending on %s has been defined")

    def get_success_message(self, cleaned_data):
        return self.success_message % (cleaned_data["start_date"], cleaned_data["end_date"])

    def form_valid(self, form):
        response = super().form_valid(form)

        copy_activities_from_id = None
        if form.cleaned_data.get("copy_activities", None):
            copy_activities_from_id = form.cleaned_data.get("copy_activities").pk

        copy_children_from_id = None
        if form.cleaned_data.get("copy_children", None):
            copy_children_from_id = form.cleaned_data.get("copy_children").pk

        create_tenant.delay(
            start=form.cleaned_data["start_date"].isoformat(),
            end=form.cleaned_data["end_date"].isoformat(),
            copy_activities_from_id=copy_activities_from_id,
            copy_children_from_id=copy_children_from_id,
            user_id=str(self.request.user.pk),
        )
        return response  # noqa: R504
