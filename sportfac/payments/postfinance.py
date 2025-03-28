import logging

from django.conf import settings
from django.urls import reverse

from postfinancecheckout import Configuration
from postfinancecheckout.api import (  # TransactionPaymentPageServiceApi,
    TransactionLightboxServiceApi,
    TransactionServiceApi,
    TransactionVoidServiceApi,
)
from postfinancecheckout.models import AddressCreate, LineItem, LineItemType, TransactionCreate
from postfinancecheckout.rest import ApiException

from .models import PostfinanceTransaction


CURR_CHF = "CHF"
DEFAULT_TIMEOUT = 5
DEFAULT_LANGUAGE = "fr"

logger = logging.getLogger(__name__)


def invoice_to_transaction(request, invoice):
    lines = []
    lines.append(
        LineItem(
            name="Inscriptions",
            unique_id=str(invoice.id),
            quantity=1,
            amount_including_tax=invoice.total,
            type=LineItemType.PRODUCT,
        )
    )

    billing_address = AddressCreate(
        city=invoice.family.city,
        country=invoice.family.country_iso_3166,
        email_address=invoice.family.email,
        family_name=invoice.family.last_name,
        given_name=invoice.family.first_name,
        postcode=invoice.family.zipcode,
        street=invoice.family.address,
    )
    if request.get_full_path().startswith(reverse("backend:bill-list")):
        success_url = "https://{}{}".format(request.get_host(), reverse("backend:bill-list"))
        fail_url = f"https://{request.get_host()}{invoice.get_pay_url()}"
    elif request.get_full_path().startswith(reverse("wizard:entry_point")):
        success_url = "https://{}{}".format(
            request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment-success"})
        )
        fail_url = "https://{}{}".format(
            request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment-failure"})
        )
    elif request.get_full_path().startswith(reverse("wizard:step", kwargs={"step_slug": "payment"})):
        success_url = "https://{}{}".format(
            request.get_host(), reverse("registrations:registrations_registered_activities")
        )
        fail_url = "https://{}{}".format(request.get_host(), reverse("wizard:step", kwargs={"step_slug": "payment"}))
    else:
        success_url = "https://{}{}".format(request.get_host(), reverse("registrations:registrations_billing"))
        fail_url = f"https://{request.get_host()}{request.get_full_path()}"

    return TransactionCreate(
        billing_address=billing_address,
        invoice_merchant_reference=invoice.billing_identifier,
        language="fr",
        line_items=lines,
        currency=CURR_CHF,
        auto_confirmation_enabled=True,  # When auto confirmation is enabled the transaction can be confirmed by the
        # user and does not require an explicit confirmation through the web service API.
        success_url=success_url,
        failed_url=fail_url,
    )


def get_transaction(request, invoice):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionServiceApi(config)
    # transaction_page_service = TransactionPaymentPageServiceApi(config)
    transaction_lightbox_service = TransactionLightboxServiceApi(config)
    transaction = invoice_to_transaction(request, invoice)
    logger.info("Transaction: %s", transaction)
    transaction_create = transaction_service.create(space_id=settings.POSTFINANCE_SPACE_ID, transaction=transaction)
    # payment_page_url = transaction_page_service.payment_page_url(
    #    space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_create.id
    # )
    javascript_url = transaction_lightbox_service.javascript_url(
        space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_create.id
    )
    return PostfinanceTransaction.objects.create(
        invoice=invoice,
        transaction_id=transaction_create.id,
        payment_page_url=javascript_url,
        status=transaction_create.state.value,
    )

    # return PostfinanceTransaction.objects.create(
    #     invoice=invoice,
    #     transaction_id=transaction_create.id,
    #     payment_page_url=payment_page_url,
    #     status=transaction_create.state.value,
    # )


def get_new_status(transaction_id):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionServiceApi(config)
    transaction = transaction_service.read(space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_id)
    return transaction.state.value, transaction


def void_transaction(transaction_id):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionVoidServiceApi(config)
    try:
        transaction_void = transaction_service.void_offline(space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_id)
    except ApiException as e:
        logger.error("Exception when calling TransactionVoidServiceApi->void_offline: %s\n", e)
        return "FAILED"
    return transaction_void.state.value
