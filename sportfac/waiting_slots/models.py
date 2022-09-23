# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.urls import reverse

from registrations.models import Registration
from sportfac.models import TimeStampedModel


class WaitingSlot(TimeStampedModel):
    child = models.ForeignKey('registrations.Child', on_delete=models.CASCADE)
    course = models.ForeignKey('activities.Course', on_delete=models.CASCADE)

    class Meta:
        ordering = ('course', 'created')
        unique_together = (('child', 'course'),)

    def get_transform_url(self):
        return reverse('backend:waiting_slot-transform', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('backend:waiting_slot-delete', kwargs={'pk': self.pk})

    def create_registration(self):
        return Registration.objects.create(
            course=self.course, child=self.child, status=Registration.STATUS.confirmed
        )

    def __repr__(self):
        return self.__unicode__()

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"{} - {}".format(self.child, self.course.short_name)

