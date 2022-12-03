# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

from async_messages import message_user
from braces.views import LoginRequiredMixin
from registrations.models import Bill
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from sportfac.views import WizardMixin

from .models import DatatransTransaction


class DatatransWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        if "transactionId" and "refno" not in data:
            raise ValidationError("missing parameters")
        invoice = get_object_or_404(Bill, billing_identifier=data.get("refno"))
        transaction = get_object_or_404(
            DatatransTransaction, transaction_id=data.get("transactionId"), invoice=invoice
        )
        if "status" in data:
            transaction.status = data.get("status")
        if "paymentMethod" in data:
            transaction.payment_method = data.get("paymentMethod")
        transaction.webhook = data
        transaction.update_invoice()
        transaction.save()

        if transaction.is_success:
            transaction.invoice.send_confirmation()
        else:
            message_user(
                transaction.invoice.family,
                _("Payment was rejected either by you or the bank"),
                "warning",
            )
        return Response("Webhook accepted")


class PaymentSuccessView(LoginRequiredMixin, WizardMixin, TemplateView):
    template_name = "payments/success.html"

    @staticmethod
    def check_initial_condition(request):
        # Condition verified externally, datatrans redirects us here.
        pass


class PaymentFailureView(LoginRequiredMixin, WizardMixin, TemplateView):
    template_name = "payments/failure.html"

    @staticmethod
    def check_initial_condition(request):
        # Condition verified externally, datatrans redirects us here.
        pass
