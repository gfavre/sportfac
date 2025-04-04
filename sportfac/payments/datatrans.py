from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language

import requests
from dateutil.relativedelta import relativedelta
from requests.auth import HTTPBasicAuth

from .models import DatatransTransaction


INITIALIZE_TRANSACTION_ENDPOINT = f"{settings.DATATRANS_API_URL.geturl()}v1/transactions"
DEFAULT_CURRENCY = "CHF"
DATATRANS_TIMEOUT_SECONDS = 5


class DataTransException(Exception):
    pass


def invoice_to_meta_data(request, invoice):
    return {
        "amount": invoice.total * 100,
        "autoSettle": True,
        "currency": DEFAULT_CURRENCY,
        "language": get_language(),
        "paymentMethods": settings.DATATRANS_PAYMENT_METHODS,
        "redirect": {
            "cancelUrl": "https://{}{}".format(
                request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment"})
            ),
            "errorUrl": "https://{}{}".format(
                request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment-failure"})
            ),
            "successUrl": "https://{}{}".format(
                request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment-success"})
            ),
        },
        "refno": invoice.billing_identifier,
    }


def get_transaction(request, invoice):
    if not invoice:
        return None
    # check if a non-expired transaction exists and return it
    non_expired_transactions = invoice.datatrans_transactions.filter(
        expiration__gte=now(), status=DatatransTransaction.STATUS.initialized
    )
    if non_expired_transactions.exists():
        return non_expired_transactions.first()
    username = int(settings.DATATRANS_USER)
    password = settings.DATATRANS_PASSWORD
    response = requests.post(
        INITIALIZE_TRANSACTION_ENDPOINT,
        json=invoice_to_meta_data(request, invoice),
        auth=HTTPBasicAuth(username, password),
        timeout=DATATRANS_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    transaction_id = response.json().get("transactionId")

    return DatatransTransaction.objects.create(
        transaction_id=int(transaction_id),
        expiration=now() + relativedelta(minutes=30),
        invoice=invoice,
    )
