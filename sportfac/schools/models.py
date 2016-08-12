from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices

from sportfac.models import TimeStampedModel


class Teacher(TimeStampedModel):
    number = models.IntegerField(db_index=True, unique=True, null=True, blank=True, 
                                 verbose_name=_("Number"))

    first_name = models.CharField(_("First name"), max_length=50)
    last_name = models.CharField(_("Last name"), max_length=50, db_index=True)
    years = models.ManyToManyField('profiles.SchoolYear', verbose_name=_("School years"))
    email = models.EmailField(verbose_name=_('Email address'), max_length=255, 
                              blank=True, null=True)

    def __unicode__(self):
        years = ' - '.join([unicode(year) for year in self.years.all()])
        return '%s %s (%s)' % (self.first_name, self.last_name, years)

    def get_full_name(self):
        return '%s %s ' % (self.first_name, self.last_name)

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


class School(TimeStampedModel):
    name = models.CharField(_("Name"), max_length=50)
    
    class Meta:
        verbose_name = _("school")
        verbose_name_plural = _("schools")