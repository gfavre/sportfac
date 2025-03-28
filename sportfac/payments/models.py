import uuid

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _

from model_utils import Choices
from model_utils.managers import QueryManager
from model_utils.models import StatusModel, TimeStampedModel


class DatatransTransaction(TimeStampedModel, StatusModel):
    # see: https://docs.datatrans.ch/docs/payment-methods
    METHODS = Choices(
        ("AZP", "Amazon Pay"),
        ("AMX", "American Express"),
        ("APL", "Apple Pay"),
        ("PAY", "Google Pay"),
        ("KLN", "Klarna"),
        ("MAU", "Maestro"),
        ("ECA", "Mastercard"),
        ("PAP", "PayPal"),
        ("PFC", "PostFinance Card"),
        ("PEF", "PostFinance E-Finance"),
        ("REK", "Reka"),
        ("SAM", "Samsung Pay"),
        ("ESY", "Swisscom Pay"),
        ("TWI", "Twint"),
        ("VIS", "Visa"),
        ("cash", "Cash"),
    )
    STATUS = Choices(
        ("initialized", _("Initialized")),  # request just opened
        ("challenge_required", _("Challenge required")),
        ("challenge_ongoing", _("Challenge ongoing")),
        ("authenticated", _("Authenticated")),
        ("authorized", _("Authorized")),  # Guess it is a successful status
        ("settled", _("Settled")),  # seems to be a success? => yes, success for credit cards
        ("canceled", _("Canceled")),
        ("transmitted", _("Transmitted")),  # The final successful status for twint
        ("failed", _("Failed")),
    )
    expiration = models.DateTimeField(null=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    invoice = models.ForeignKey("registrations.Bill", related_name="datatrans_transactions", on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=4, choices=METHODS, default=METHODS.TWI)
    transaction_id = models.BigIntegerField(db_index=True)
    webhook = JSONField(null=True, blank=True)

    objects = models.Manager()
    successful = QueryManager(status__in=("authorized", "settled", "transmitted"))

    class Meta:
        ordering = ("-expiration",)

    @property
    def is_success(self):
        return self.status in (
            self.STATUS.authorized,
            self.STATUS.settled,
            self.STATUS.transmitted,
        )

    @property
    def refno(self):
        return self.invoice.billing_identifier

    @property
    def script_url(self):
        return f"{settings.DATATRANS_PAY_URL.geturl()}upp/payment/js/datatrans-2.0.0.js"

    def update_invoice(self):
        if self.is_success:
            self.invoice.set_paid()
        elif self.status in (self.STATUS.canceled, self.STATUS.failed) and not self.invoice.is_paid:
            self.invoice.set_waiting()

    def __str__(self):
        return f"{self.invoice} {self.status}"


class PostfinanceTransaction(TimeStampedModel, StatusModel):
    STATUS = Choices(
        ("PENDING", _("Pending")),  # The transaction is created but it is not confirmed by the merchant system.
        (
            "CONFIRMED",
            _("Confirmed"),
        ),  # The transaction is created and confirmed however the processing has not yet started.
        ("PROCESSING", _("Processing")),  # The transaction is processing.
        ("FAILED", _("Failed")),  # The transaction authorization failed.
        ("AUTHORIZED", _("Authorized")),  # The transaction is authorized.
        ("COMPLETED", _("Completed")),  # The transaction is completed.
        ("FULFILL", _("Fulfill")),  # The transaction is ready to be delivered.
        ("DECLINE", _("Decline")),  # The goods or services should not be delivered.
        ("VOIDED", _("Voided")),  # The authorization is voided and hence no money is transfered.
    )

    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    invoice = models.ForeignKey(
        "registrations.Bill", related_name="postfinance_transactions", on_delete=models.CASCADE
    )
    transaction_id = models.BigIntegerField(db_index=True)
    payment_page_url = models.URLField(null=True, blank=True)
    payment_method = models.CharField(max_length=255, blank=True, default="")
    webhook = JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    @property
    def is_pending(self):
        return self.status in (self.STATUS.PENDING, self.STATUS.CONFIRMED, self.STATUS.PROCESSING)

    @property
    def is_success(self):
        return self.status in (
            self.STATUS.AUTHORIZED,
            self.STATUS.COMPLETED,
            self.STATUS.FULFILL,
        )

    @property
    def refno(self):
        return self.invoice.billing_identifier

    def update_invoice(self):
        if self.is_success:
            self.invoice.set_paid()
        elif self.status in (self.STATUS.FAILED, self.STATUS.DECLINE, self.STATUS.VOIDED) and not self.invoice.is_paid:
            self.invoice.set_waiting()

    def update_status(self):
        from .postfinance import get_new_status

        status, pf_transaction = get_new_status(self.transaction_id)
        self.status = status
        self.webhook = pf_transaction.to_dict()
        try:
            self.payment_method = pf_transaction.payment_connector_configuration.name
            self.save(update_fields=("status", "webhook", "payment_method"))
        except AttributeError:
            self.save(update_fields=("status", "webhook"))

    def void(self):
        from .postfinance import void_transaction

        void_status = void_transaction(self.transaction_id)
        if void_status in ("SUCCESSFUL", "FAILED"):
            # the failed status can happen if the transaction is already voided
            self.status = self.STATUS.VOIDED
            self.save(update_fields=("status",))
            self.update_invoice()

    def __str__(self):
        return f"{self.transaction_id} - {self.status}"
