from django.conf import settings
from django.urls import reverse

from postfinancecheckout import Configuration
from postfinancecheckout.api import TransactionPaymentPageServiceApi, TransactionServiceApi
from postfinancecheckout.models import AddressCreate, LineItem, LineItemType, TransactionCreate

from .models import PostfinanceTransaction


CURR_CHF = "CHF"
DEFAULT_TIMEOUT = 5
DEFAULT_LANGUAGE = "fr"


def invoice_to_transaction(request, invoice):
    lines = []
    for registration in invoice.registrations.all():
        if registration.price == 0:
            continue
        lines.append(
            LineItem(
                name=f"{ registration.course.activity.name } - {registration.child.full_name}",
                unique_id=str(registration.id),
                quantity=1,
                amount_including_tax=registration.price,
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
    elif request.get_full_path().startswith(reverse("wizard_billing")):
        success_url = "https://{}{}".format(request.get_host(), reverse("wizard_payment_success"))
        fail_url = "https://{}{}".format(request.get_host(), reverse("wizard_billing"))
    else:
        success_url = "https://{}{}".format(request.get_host(), reverse("registrations:registrations_billing"))
        fail_url = f"https://{request.get_host()}{request.get_full_path()}"

    return TransactionCreate(
        billing_address=billing_address,
        invoiceMerchantReference=invoice.billing_identifier,
        language="fr",
        line_items=lines,
        currency=CURR_CHF,
        autoConfirmationEnabled=True,  # When auto confirmation is enabled the transaction can be confirmed by the user
        # and does not require an explicit confirmation through the web service API.
        successUrl=success_url,
        failedUrl=fail_url,
    )


def get_transaction(request, invoice):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionServiceApi(config)
    transaction_page_service = TransactionPaymentPageServiceApi(config)

    transaction = invoice_to_transaction(request, invoice)
    transaction_create = transaction_service.create(space_id=settings.POSTFINANCE_SPACE_ID, transaction=transaction)
    payment_page_url = transaction_page_service.payment_page_url(
        space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_create.id
    )
    return PostfinanceTransaction.objects.create(
        invoice=invoice,
        transaction_id=transaction_create.id,
        payment_page_url=payment_page_url,
        status=transaction_create.state.value,
    )


def get_new_status(transaction_id):
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=DEFAULT_TIMEOUT,
    )
    transaction_service = TransactionServiceApi(config)
    transaction = transaction_service.read(space_id=settings.POSTFINANCE_SPACE_ID, id=transaction_id)
    return transaction.state.value
