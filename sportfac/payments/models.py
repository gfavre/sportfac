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
    STATUS = Choices(
        ('initialized', _("Initialized")),
        ("challenge_required", _("Challenge required")),
        ("challenge_ongoing", _("Challenge ongoing")),
        ("authenticated", _("Authenticated")),
        ("authorized", _("Authorized")),
        ("settled", _("Settled")),
        ("canceled", _("Canceled")),
        ("transmitted", _("Transmitted")),
        ("failed", _("Failed")),
    )
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    invoice = models.ForeignKey('registrations.Bill', related_name='datatrans_transactions')
    transaction_id = models.BigIntegerField(db_index=True)
    webhook = JSONField(null=True, blank=True)
    expiration = models.DateTimeField(null=True)

    class Meta:
        ordering = ('-expiration',)

    @property
    def is_success(self):
        return self.status == self.STATUS.authorized

    @property
    def refno(self):
        return self.invoice.billing_identifier

    @property
    def script_url(self):
        return '{}upp/payment/js/datatrans-2.0.0.js'.format(settings.DATATRANS_PAY_URL.geturl())

    def update_invoice(self):
        if self.status == self.STATUS.authorized:
            self.invoice.set_paid()
        elif self.status in (self.STATUS.canceled, self.STATUS.failed) and not self.invoice.is_paid:
            self.invoice.set_waiting()




