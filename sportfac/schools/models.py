from __future__ import unicode_literals

from __future__ import absolute_import
from django.urls import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

from sportfac.models import TimeStampedModel
import six


class Teacher(TimeStampedModel):
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True,
                                 verbose_name=_("Number"))

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50, db_index=True)
    years = models.ManyToManyField('profiles.SchoolYear', verbose_name=_("School years"))
    email = models.EmailField(verbose_name=_('Email address'), max_length=255,
                              blank=True, null=True)
    buildings = models.ManyToManyField('Building', verbose_name=_("Building"), related_name='teachers',
                                       blank=True)

    class Meta:
        ordering = ('last_name', 'first_name')

    def __unicode__(self):
        years = ' - '.join([six.text_type(year) for year in self.years.all()])
        return '%s %s (%s)' % (self.first_name, self.last_name, years)

    def get_full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    @property
    def full_name(self):
        return self.get_full_name()

    def get_update_url(self):
        return reverse('backend:teacher-update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('backend:teacher-delete', kwargs={'pk': self.pk})

    def get_backend_url(self):
        return reverse('backend:teacher-detail', kwargs={'pk': self.pk})

    @property
    def years_label(self):
        return ', '.join([str(year) for year in self.years.all()])

    class Meta:
        ordering = ('last_name', 'first_name')
        verbose_name = _("teacher")
        verbose_name_plural = _("teachers")


class Building(TimeStampedModel):
    COUNTRY = Choices(('CH', _("Switzerland")),
                      ('FL', _("Liechtenstein")),
                      ('D', _("Germany")),
                      ('F', _("France")),
                      ('I', _("Italy")),
                      ('A', _("Austria")))

    name = models.CharField(_("Building name"), max_length=100)
    external_id = models.CharField(_("Identifier"), max_length=50, blank=True)
    address = models.TextField(_("Street"), blank = True)
    zipcode = models.CharField(_("NPA"), blank=True, max_length=5)
    city = models.CharField(_('City'), max_length=100, blank=True)
    country = models.CharField(_('Country'), max_length=2, choices=COUNTRY, default=COUNTRY.CH)

    class Meta:
        verbose_name = _("building")
        verbose_name_plural = _("buildings")

    def __unicode__(self):
        return self.name

    def get_update_url(self):
        return reverse('backend:building-update', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('backend:building-delete', kwargs={'pk': self.pk})

    def get_backend_url(self):
        return reverse('backend:building-detail', kwargs={'pk': self.pk})
