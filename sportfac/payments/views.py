from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from api.permissions import PostfinanceIPFilterPermission
from async_messages import message_user
from braces.views import LoginRequiredMixin
from registrations.models import Bill
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from sportfac.views import WizardMixin

from .models import DatatransTransaction, PostfinanceTransaction


class DatatransWebhookView(APIView):
    permission_classes = [AllowAny]

    # noinspection PyMethodMayBeStatic
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
        # Condition verified externally, payment provider redirects us here.
        pass


class PaymentFailureView(LoginRequiredMixin, WizardMixin, TemplateView):
    template_name = "payments/failure.html"

    @staticmethod
    def check_initial_condition(request):
        # Condition verified externally, payment provider redirects us here.
        pass


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
        transaction = PostfinanceTransaction.objects.filter(transaction_id=data.get("entityId")).first()
        if not transaction:
            return Response("Webhook accepted but not handled")

        transaction.update_status()
        transaction.update_invoice()

        if not transaction.is_success:
            message_user(
                transaction.invoice.family,
                _("Payment was rejected either by you or the bank"),
                "warning",
            )
        return Response("Webhook accepted")
