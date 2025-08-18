import logging

import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language
from requests.auth import HTTPBasicAuth

from .models import DatatransTransaction


INITIALIZE_TRANSACTION_ENDPOINT = f"{settings.DATATRANS_API_URL.geturl()}v1/transactions"
DEFAULT_CURRENCY = "CHF"
DATATRANS_TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)


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
    print(">>> get_transaction CALLED <<<")
    if not invoice:
        return None

    username = int(settings.DATATRANS_USER)
    password = settings.DATATRANS_PASSWORD
    response = requests.post(
        INITIALIZE_TRANSACTION_ENDPOINT,
        json=invoice_to_meta_data(request, invoice),
        auth=HTTPBasicAuth(username, password),
        timeout=DATATRANS_TIMEOUT_SECONDS,
    )
    logger.info("Datatrans API response: %s", response.json())
    print(response.json())
    response.raise_for_status()
    transaction_id = response.json().get("transactionId")

    trx = DatatransTransaction.objects.create(
        transaction_id=transaction_id,
        expiration=now() + relativedelta(minutes=30),
        invoice=invoice,
    )
    logger.info("Created DatatransTransaction pk=%s, transactionId=%s", trx.pk, trx.transaction_id)
    print(trx.transaction_id)
    return trx
