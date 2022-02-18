# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.contrib.postgres.fields import JSONField
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel, TimeStampedModel


class DatatransTransaction(TimeStampedModel, StatusModel):
    # see: https://docs.datatrans.ch/docs/payment-methods
    METHODS = Choices(
        ('AZP', "Amazon Pay"),
        ('AMX', "American Express"),
        ('APL', "Apple Pay"),
        ('PAY', "Google Pay"),
        ('KLN', "Klarna"),
        ('MAU', "Maestro"),
        ('ECA', "Mastercard"),
        ('PAP', "PayPal"),
        ('PFC', "PostFinance Card"),
        ('PEF', "PostFinance E-Finance"),
        ('REK', "Reka"),
        ('SAM', "Samsung Pay"),
        ('ESY', "Swisscom Pay"),
        ('TWI', "Twint"),
        ('VIS', "Visa"),
    )
    STATUS = Choices(
        ('initialized', _("Initialized")),  # request just opened
        ("challenge_required", _("Challenge required")),
        ("challenge_ongoing", _("Challenge ongoing")),
        ("authenticated", _("Authenticated")),
        ("authorized", _("Authorized")),  # Guess it is a successful status
        ("settled", _("Settled")),  # seems to be a success?
        ("canceled", _("Canceled")),
        ("transmitted", _("Transmitted")),  # The final successful status for twint
        ("failed", _("Failed")),
    )
    expiration = models.DateTimeField(null=True)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    invoice = models.ForeignKey('registrations.Bill', related_name='datatrans_transactions')
    payment_method = models.CharField(max_length=3, choices=METHODS, default=METHODS.TWI)
    transaction_id = models.BigIntegerField(db_index=True)
    webhook = JSONField(null=True, blank=True)

    class Meta:
        ordering = ('-expiration',)

    @property
    def is_success(self):
        return self.status in (self.STATUS.authorized, self.STATUS.transmitted)

    @property
    def refno(self):
        return self.invoice.billing_identifier

    @property
    def script_url(self):
        return '{}upp/payment/js/datatrans-2.0.0.js'.format(settings.DATATRANS_PAY_URL.geturl())

    def update_invoice(self):
        if self.is_success:
            self.invoice.set_paid()
        elif self.status in (self.STATUS.canceled, self.STATUS.failed) and not self.invoice.is_paid:
            self.invoice.set_waiting()




