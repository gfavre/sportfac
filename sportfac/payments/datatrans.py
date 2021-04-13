# -*- coding: utf-8 -*-
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import get_language

from dateutil.relativedelta import relativedelta
import requests
from requests.auth import HTTPBasicAuth

from .models import DatatransTransaction

INITIALIZE_TRANSACTION_ENDPOINT = '{}v1/transactions'.format(settings.DATATRANS_API_URL.geturl())
DEFAULT_CURRENCY = 'CHF'
DATATRANS_TIMEOUT_SECONDS = 5


def invoice_to_meta_data(request, invoice):
    return {
        'amount': invoice.total * 100,
        'autoSettle': True,
        'currency': DEFAULT_CURRENCY,
        'language': get_language(),
        'paymentMethods': settings.DATATRANS_PAYMENT_METHODS,
        'redirect': {
            'successUrl': 'https://{}{}'.format(request.get_host(), reverse('wizard_payment_success')),
            'cancelUrl': 'https://{}{}'.format(request.get_host(), reverse('wizard_billing')),
            'errorUrl': 'https://{}{}'.format(request.get_host(), reverse('wizard_billing')),
        },
        'refno': invoice.billing_identifier,
    }


def get_transaction(request, invoice):
    # check if a non-expired transaction exists and return it
    if invoice.datatrans_transactions.exclude(expiration__lte=now(),
                                              status=DatatransTransaction.STATUS.initialized).exists():
        return invoice.datatrans_transactions.exclude(expiration__lte=now(),
                                                      status=DatatransTransaction.STATUS.initialized).get()
    try:
        username = int(settings.DATATRANS_USER)
        password = settings.DATATRANS_PASSWORD
        response = requests.post(
            INITIALIZE_TRANSACTION_ENDPOINT,
            json=invoice_to_meta_data(request, invoice),
            auth=requests.auth.HTTPBasicAuth(username, password),
            timeout=DATATRANS_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        details = e.response.json()
        raise e
    transaction_id = response.json().get('transactionId')

    return DatatransTransaction.objects.create(
        transaction_id=int(transaction_id),
        expiration=now() + relativedelta(minutes=30),
        invoice=invoice
    )
