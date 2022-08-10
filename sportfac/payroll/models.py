# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from sportfac.models import TimeStampedModel


class Function(TimeStampedModel):
    RATE_MODES = (
        ('hourly', _('Hourly')),
        ('daily', _('Daily')),
        ('monthly', _('Monthly')),
    )
    code = models.CharField(_("Function code"), max_length=30, unique=True)
    name = models.CharField(_("Function name"), max_length=100)
    rate = models.DecimalField(verbose_name=_("Rate"), max_digits=10, decimal_places=2)
    rate_mode = models.CharField(verbose_name=_("Rate mode"), max_length=20, choices=RATE_MODES)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.__str__()

    def get_delete_url(self):
        return reverse('backend:function-delete', kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse('backend:function-update', kwargs={"pk": self.pk})
