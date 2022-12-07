# -*- coding: utf-8 -*-
import datetime
import os
from collections import OrderedDict
from tempfile import mkdtemp
import urllib.parse

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from activities.forms import AllocationAccountForm
from activities.models import AllocationAccount
from dateutil.relativedelta import relativedelta
from payments.models import DatatransTransaction

from .mixins import BackendMixin


__all__ = [
    "AllocationAccountListView",
    "AllocationAccountCreateView",
    "AllocationAccountUpdateView",
    "AllocationAccountDeleteView",
    "AllocationAccountReportView",
]


class AllocationAccountReportView(BackendMixin, ListView):
    model = AllocationAccount
    template_name = "backend/allocations/report.html"

    def get_context_data(self, **kwargs):
        context = super(AllocationAccountReportView, self).get_context_data(**kwargs)
        context["start"] = (now() - relativedelta(days=29)).date()
        context["end"] = now().date()

        if "start" in self.request.GET:
            try:
                context["start"] = datetime.datetime.strptime(
                    self.request.GET.get("start"), "%Y-%m-%d"
                ).date()
            except ValueError:
                pass
        if "end" in self.request.GET:
            try:
                context["end"] = datetime.datetime.strptime(
                    self.request.GET.get("end"), "%Y-%m-%d"
                ).date()
            except ValueError:
                pass

        context["object_list"] = AllocationAccount.objects.prefetch_related(
            "registrations",
            "registrations__bill",
            "registrations__course",
            "registrations__course__activity",
            "registrations__bill__datatrans_transactions",
        )
        registrations_method_tmpl = "{}_period_registrations"
        total_method_tmpl = "{}_period_total"

        all_payment_methods = ["cash"] + settings.DATATRANS_PAYMENT_METHODS

        for allocation_account in context["object_list"]:
            registrations = allocation_account.get_registrations(context["start"], context["end"])
            allocation_account.period_registrations = registrations
            allocation_account.period_total = sum(
                [registration.price for registration in registrations if registration.paid]
            )
            for method in all_payment_methods:
                method_list = [
                    registration
                    for registration in registrations
                    if registration.payment_method == method
                ]
                setattr(allocation_account, registrations_method_tmpl.format(method), method_list)
                setattr(
                    allocation_account,
                    total_method_tmpl.format(method),
                    sum([registration.price for registration in method_list]),
                )

        sections = OrderedDict()
        for method in all_payment_methods:
            section = {
                "title": DatatransTransaction.METHODS[method],
                "subsections": [],
            }
            for account in context["object_list"]:
                section["subsections"].append(
                    {
                        "title": str(account),
                        "registrations": getattr(
                            account, registrations_method_tmpl.format(method)
                        ),
                        "total": getattr(account, total_method_tmpl.format(method)),
                    }
                )
            sections[method] = section

        context["sections"] = sections

        url = self.request.get_full_path()
        url_parts = list(urllib.parse.urlparse(url))
        query = dict(urllib.parse.parse_qsl(url_parts[4]))
        query.update(pdf=1)
        url_parts[4] = urllib.parse.urlencode(query)
        context["pdf_url"] = urllib.parse.urlunparse(url_parts)
        return context

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        if "pdf" in self.request.GET:
            from backend.utils import AllocationReportPDFRenderer

            context = self.get_context_data(request=self.request)
            renderer = AllocationReportPDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = "{}-{}-{}.pdf".format(
                _("allocations"), context["start"].isoformat(), context["end"].isoformat()
            )
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            response = HttpResponse(open(filepath).read(), content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(filename)
            return response
        return super(AllocationAccountReportView, self).get(request, *args, **kwargs)


class AllocationAccountListView(BackendMixin, ListView):
    model = AllocationAccount
    template_name = "backend/allocations/list.html"


class AllocationAccountCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = AllocationAccount
    form_class = AllocationAccountForm
    success_url = reverse_lazy("backend:allocation-list")
    success_message = _(
        '<a href="%(url)s" class="alert-link">Allocation account (%(number)s)</a> has been created.'
    )
    template_name = "backend/allocations/create.html"

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.account})


class AllocationAccountUpdateView(SuccessMessageMixin, BackendMixin, UpdateView):
    model = AllocationAccount
    form_class = AllocationAccountForm
    success_url = reverse_lazy("backend:allocation-list")
    success_message = _(
        '<a href="%(url)s" class="alert-link">Allocation account (%(number)s)</a> has been updated.'
    )
    template_name = "backend/allocations/update.html"

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.account})


class AllocationAccountDeleteView(SuccessMessageMixin, BackendMixin, DeleteView):
    model = AllocationAccount
    success_message = _("Allocation has been deleted.")
    success_url = reverse_lazy("backend:allocation-list")
    template_name = "backend/allocations/confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        identifier = self.get_object().account
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _("Allocation account %(identifier)s has been deleted.") % {"identifier": identifier},
        )
        return super(AllocationAccountDeleteView, self).delete(request, *args, **kwargs)
