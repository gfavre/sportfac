# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from activities.models import RATE_MODES
from sportfac.models import TimeStampedModel


class Function(TimeStampedModel):

    code = models.CharField(_("Function code"), max_length=30, unique=True)
    name = models.CharField(_("Function name"), max_length=100)
    rate = models.DecimalField(verbose_name=_("Rate"), max_digits=10, decimal_places=2, blank=True, null=True)
    rate_mode = models.CharField(verbose_name=_("Rate mode"), max_length=20, choices=RATE_MODES)

    class Meta:
        ordering = ['code']

    @property
    def is_hourly(self):
        return self.rate_mode == RATE_MODES.hour

    @property
    def is_daily(self):
        return self.rate_mode == RATE_MODES.day

    def get_delete_url(self):
        return reverse('backend:function-delete', kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse('backend:function-update', kwargs={"pk": self.pk})

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.__str__()



class Payroll(TimeStampedModel):
    start = models.DateField(_("Start date"))
    end = models.DateField(_("End date"))
    set_as_exported = models.BooleanField(_("Set as exported"), default=True)
    include_already_exported = models.BooleanField(_("Include already exported sessions"), default=False)
    add_details = models.BooleanField(_("Add details"), default=False)
    csv_file = models.FileField(upload_to='payroll', blank=True, null=True)
    exported_by = models.ForeignKey('profiles.FamilyUser', verbose_name=_("Exported by"), blank=True, null=True)

    def generate_csv(self):
        from .utils import get_payroll_csv
        filelike = BytesIO()
        get_payroll_csv(self, filelike)
        self.csv_file.save(
            "{start}_{end}.csv".format(start=self.start, end=self.end),
            ContentFile(filelike.getvalue()))

