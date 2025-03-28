import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from async_messages import message_user
from braces.views import LoginRequiredMixin
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.permissions import PostfinanceIPFilterPermission
from appointments.models import Appointment
from registrations.models import Bill
from wizard.views import BaseWizardStepView
from .models import DatatransTransaction, PostfinanceTransaction


logger = logging.getLogger(__name__)


class DatatransWebhookView(APIView):
    permission_classes = [AllowAny]

    # noinspection PyMethodMayBeStatic
    def post(self, request, *args, **kwargs):
        data = request.data
        logger.info("webhook received: %s", data)
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


class WizardPaymentSuccessView(LoginRequiredMixin, BaseWizardStepView, TemplateView):
    step_slug = "payment-success"
    template_name = "wizard/payment-success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bill"] = self.request.user.bills.order_by("-created").first()
        if settings.KEPCHUP_USE_APPOINTMENTS:
            context["include_calendar"] = True
            context["appointments"] = Appointment.objects.filter(family=self.request.user)
        return context


class WizardPaymentFailureView(LoginRequiredMixin, BaseWizardStepView, TemplateView):
    step_slug = "payment-failure"
    template_name = "wizard/payment-failure.html"


class PostfinanceWebhookView(APIView):
    permission_classes = [PostfinanceIPFilterPermission]

    # noinspection PyMethodMayBeStatic
    def post(self, request, *args, **kwargs):
        data = request.data
        if "entityId" and "spaceId" not in data:
            raise ValidationError("missing parameters")
        if data["spaceId"] != settings.POSTFINANCE_SPACE_ID:
            raise ValidationError("invalid spaceId")
        # Note: normally the following line would be the perfect way to do get the transaction object.
        # transaction = get_object_or_404(PostfinanceTransaction, transaction_id=data.get("entityId"))
        # However, in the case of Montreux we have 2 separate sites, but a single contract. Postfinance can't set a
        # webhook location different for each postfinance-user-id. The administrative wa to handle this issue is to
        # create another space, but that requires another contract, and another contract requires a lot of time.
        # Therefore we have 2 webhook adresses on which every transaction is sent, regardless of the kepchup instance.
        # These webhooks would generate a 404 error on the other instance, so we have to silence it.
        # This is not very elegant, but it alleviates the administration burden.
        logger.info("webhook received: %s", data)
        transaction = PostfinanceTransaction.objects.filter(transaction_id=data.get("entityId")).first()
        if not transaction:
            return Response("Webhook accepted but not handled")
        was_pending = transaction.is_pending
        transaction.update_status()
        transaction.update_invoice()
        if transaction.is_success and was_pending:
            # we receive at least 5 webhooks for the same transaction, so we only send the confirmation once
            transaction.invoice.send_confirmation()
        else:
            message_user(
                transaction.invoice.family,
                _("Payment was rejected either by you or the bank"),
                "warning",
            )
        return Response("Webhook accepted")
