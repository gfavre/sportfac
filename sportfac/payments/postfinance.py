from django.urls import reverse

from postfinancecheckout.models import AddressCreate, LineItem, LineItemType, TransactionCreate


CURR_CHF = "CHF"


def invoice_to_transaction(request, invoice):
    #         self.total = sum([registration.price for registration in self.registrations.all() if registration.price])
    lines = []
    for registration in invoice.registrations.all():
        if registration.price == 0:
            continue
        lines.append(
            LineItem(
                name=f"{ registration.course.activity.name } - {registration.child.full_name}",
                unique_id=registration.id,
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
    success_url = "https://{}{}".format(request.get_host(), reverse("wizard_payment_success"))
    fail_url = "https://{}{}".format(request.get_host(), reverse("wizard_billing"))

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
