# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import TemplateView

from braces.views import LoginRequiredMixin
from rest_framework.views import APIView

from sportfac.views import WizardMixin
from .models import DatatransTransaction


class DatatransWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        transaction, created = DatatransTransaction.objects.get_or_create(
            transaction_id=data.get('transactionId'), invoice__code=data.get('refno'))
        transaction.webhook = data
        transaction.status = data.get('status')
        transaction.update_invoice()


class PaymentSuccessView(LoginRequiredMixin, WizardMixin, TemplateView):
    template_name = 'payments/success.html'

    @staticmethod
    def check_initial_condition(request):
        # Condition verified externally, datatrans redirects us here.
        pass


class PaymentFailureView(LoginRequiredMixin, WizardMixin, TemplateView):
    template_name = 'payments/failure.html'

    @staticmethod
    def check_initial_condition(request):
        # Condition verified externally, datatrans redirects us here.
        pass
