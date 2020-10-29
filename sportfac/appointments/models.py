# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _, ugettext

from model_utils.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField


class AppointmentSlot(TimeStampedModel):
    title = models.CharField(null=True, blank=True, max_length=50, verbose_name=_("Displayed name"))
    places = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ('start', 'end')
        verbose_name = _("Appointment slot")
        verbose_name_plural = _("Appointment slots")

    @property
    def available_places(self):
        if hasattr(self, 'appointments'):
            return self.places - self.appointments.count()
        return self.places

    @property
    def api_register_url(self):
        return reverse('api:register_slots', kwargs={'slot_id': self.id})

    @property
    def api_management_url(self):
        return reverse('api:slots-detail', kwargs={'pk': self.id})

    def __unicode__(self):
        return self.start.isoformat() + ' - ' + self.end.isoformat()


class Appointment(TimeStampedModel):
    slot = models.ForeignKey('AppointmentSlot', on_delete=models.CASCADE, related_name='appointments')
    child = models.OneToOneField('registrations.Child', on_delete=models.CASCADE,
                                 related_name='appointment')
    family = models.ForeignKey('profiles.FamilyUser', null=True, on_delete=models.SET_NULL, related_name='appointments')
    email = models.CharField(_("Email"), blank=True, null=True, max_length=255)
    phone_number = PhoneNumberField(_("Phone number"), max_length=30, blank=True)

    @property
    def get_backend_delete_url(self):
        return reverse('backend:appointment-delete', kwargs={'appointment': self.pk})

    def __unicode__(self):
        return '{} - {}'.format(self.child, self.slot.start.strftime('%d.%m.%Y - %Hh%M'))
