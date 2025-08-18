import json
import logging

from braces.views import LoginRequiredMixin
from braces.views import UserPassesTestMixin
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import TemplateView

from profiles.models import School

from ..models import Bill
from ..models import Child
from ..models import Registration
from .utils import BillMixin
from .utils import PaymentMixin


logger = logging.getLogger(__name__)


class BillingView(LoginRequiredMixin, BillMixin, ListView):
    template_name = "registrations/billing.html"

    def get_queryset(self):
        return Bill.objects.filter(family=self.request.user).order_by("created")


class BillDetailView(LoginRequiredMixin, PaymentMixin, BillMixin, DetailView):
    """
    Display the bill (family user view)
    """

    context_object_name = "invoice"
    template_name = "registrations/invoice-detail.html"

    def get_queryset(self):
        if self.request.user.is_manager:
            return Bill.objects.all()
        return Bill.objects.filter(family=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()
        context["registrations"] = invoice.registrations.all()
        for reg in context["registrations"]:
            reg.row_span = 1 + reg.extra_infos.count()
        context["rentals"] = invoice.rentals.all()
        context["total_amount"] = invoice.total
        return context


class ChildrenListView(LoginRequiredMixin, ListView):
    template_name = "registrations/children.html"
    context_object_name = "children"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if settings.KEPCHUP_CHILD_SCHOOL:
            context["schools"] = json.dumps(list(School.objects.filter(selectable=True).values("id", "name")))
        else:
            context["school"] = json.dumps([])
        return context

    def get_queryset(self):
        return Child.objects.filter(family=self.request.user).order_by("first_name")


class InstructorMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports responsible"""

    pk_url_kwarg = "pk"

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Registration, pk=pk)

    def test_func(self, user):
        # noinspection PyUnresolvedReferences
        if self.pk_url_kwarg in self.kwargs:
            course = self.get_object().course
            return user.is_active and user.is_instructor_of(course)
        return user.is_active and user.is_instructor


class RegistrationDeleteView(InstructorMixin, DeleteView):
    model = Registration
    template_name = "registrations/confirm_cancel.html"

    def get_success_url(self):
        return self.object.course.get_absolute_url()

    def delete(self, request, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object: Registration = self.get_object()
        success_url = self.get_success_url()
        try:
            self.object.cancel(reason=Registration.REASON.instructor, user=request.user)
            self.object.save()
        except IntegrityError:
            # The registration for child and course existed previously and
            # was already canceled. We do not need to cancel it again
            self.object.delete()
        messages.add_message(self.request, messages.SUCCESS, _("Registration has been canceled."))
        return HttpResponseRedirect(success_url)


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "registrations/summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registered_list"] = self.request.user.get_registrations()
        return context
