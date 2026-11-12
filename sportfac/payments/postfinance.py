import logging
from time import sleep

from django.conf import settings
from django.db import connection
from django.urls import reverse
from postfinancecheckout import Configuration
from postfinancecheckout.api import TransactionLightboxServiceApi  # TransactionPaymentPageServiceApi,
from postfinancecheckout.api import TransactionServiceApi
from postfinancecheckout.api import TransactionVoidServiceApi
from postfinancecheckout.models import AddressCreate
from postfinancecheckout.models import LineItem
from postfinancecheckout.models import LineItemType
from postfinancecheckout.models import TransactionCreate
from postfinancecheckout.rest import ApiException
from urllib3.exceptions import ConnectTimeoutError
from urllib3.exceptions import HTTPError
from urllib3.exceptions import MaxRetryError
from urllib3.exceptions import ProtocolError
from urllib3.exceptions import ReadTimeoutError

from .models import PostfinanceTransaction


CURR_CHF = "CHF"
DEFAULT_TIMEOUT = 7
DEFAULT_LANGUAGE = "fr"
MAX_ATTEMPTS = 2
RETRY_DELAY = 0.5
TEMPORARY_PROVIDER_STATUSES = (500, 502, 503, 504)

logger = logging.getLogger(__name__)


class PostfinanceUnavailableError(Exception):
    """Checkout is unavailable after any safe, bounded retry."""


def call_postfinance(call, *, operation, read_only=False, invoice_id=None, remote_id=None, **kwargs):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return call(**kwargs)
        except (HTTPError, ApiException) as error:
            reason = error.reason if isinstance(error, MaxRetryError) else error
            # ConnectTimeoutError includes NewConnectionError and NameResolutionError.
            # Read/protocol failures and HTTP responses cannot prove a POST was not processed.
            safe = isinstance(reason, ConnectTimeoutError)
            if read_only:
                safe = (
                    safe
                    or isinstance(reason, (ReadTimeoutError, ProtocolError))
                    or (isinstance(error, ApiException) and error.status in TEMPORARY_PROVIDER_STATUSES)
                )
            if not safe or attempt == MAX_ATTEMPTS:
                raise
            logger.warning(
                "PostFinance retry schema=%s invoice=%s operation=%s remote_id=%s attempt=%s error_type=%s",
                getattr(connection, "schema_name", "unknown"),
                invoice_id,
                operation,
                remote_id,
                attempt + 1,
                type(reason).__name__,
            )
            sleep(RETRY_DELAY)


def invoice_to_transaction(request, invoice, fail_url=None):
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
        fail_url = fail_url or f"https://{request.get_host()}{request.get_full_path()}"

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


def get_transaction(request, invoice, fail_url=None):
    stage = "prepare_transaction"
    remote_id = None
    try:
        config = Configuration(
            user_id=settings.POSTFINANCE_USER_ID,
            api_secret=settings.POSTFINANCE_API_SECRET,
            request_timeout=DEFAULT_TIMEOUT,
        )
        transaction_service = TransactionServiceApi(config)
        # transaction_page_service = TransactionPaymentPageServiceApi(config)
        transaction_lightbox_service = TransactionLightboxServiceApi(config)
        transaction = invoice_to_transaction(request, invoice, fail_url=fail_url)
        stage = "create_remote_transaction"
        transaction_create = call_postfinance(
            transaction_service.create,
            operation=stage,
            invoice_id=invoice.pk,
            space_id=settings.POSTFINANCE_SPACE_ID,
            transaction=transaction,
        )
        # payment_page_url = transaction_page_service.payment_page_url(
        #    space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_create.id
        # )
        remote_id = transaction_create.id
        stage = "get_payment_script"
        javascript_url = call_postfinance(
            transaction_lightbox_service.javascript_url,
            operation=stage,
            read_only=True,
            invoice_id=invoice.pk,
            remote_id=remote_id,
            space_id=settings.POSTFINANCE_SPACE_ID,
            id=transaction_create.id,
        )
        stage = "save_local_transaction"
        return PostfinanceTransaction.objects.create(
            invoice=invoice,
            transaction_id=transaction_create.id,
            payment_page_url=javascript_url,
            status=transaction_create.state.value,
        )

    except Exception as error:
        # SDK exception strings can contain headers, secrets and customer data.
        unavailable = stage in ("create_remote_transaction", "get_payment_script") and (
            isinstance(error, HTTPError)
            or isinstance(error, ApiException)
            and error.status in TEMPORARY_PROVIDER_STATUSES
        )
        log = logger.warning if unavailable else logger.error
        log(
            "PostFinance creation failed schema=%s invoice=%s stage=%s remote_id=%s error_type=%s provider_status=%s",
            getattr(connection, "schema_name", "unknown"),
            invoice.pk,
            stage,
            remote_id,
            type(error).__name__,
            error.status if isinstance(error, ApiException) else None,
        )
        if unavailable:
            raise PostfinanceUnavailableError("PostFinance checkout is unavailable") from error
        raise

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
    transaction = call_postfinance(
        transaction_service.read,
        operation="read_status",
        read_only=True,
        remote_id=transaction_id,
        space_id=settings.POSTFINANCE_SPACE_ID,
        id=transaction_id,
    )
    return transaction.state.value, transaction


def void_transaction(transaction_id):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionVoidServiceApi(config)
    try:
        transaction_void = call_postfinance(
            transaction_service.void_offline,
            operation="void_transaction",
            remote_id=transaction_id,
            space_id=settings.POSTFINANCE_SPACE_ID,
            id=transaction_id,
        )
    except ApiException as e:
        logger.error("PostFinance void failed remote_id=%s provider_status=%s", transaction_id, e.status)
        return "FAILED"
    return transaction_void.state.value
