# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from sportfac.models import TimeStampedModel


class WaitingSlot(TimeStampedModel):
    child = models.ForeignKey('registrations.Child', on_delete=models.CASCADE)
    course = models.ForeignKey('activities.Course', on_delete=models.CASCADE)

    class Meta:
        ordering = ('course', 'created')
        unique_together = (('child', 'course'),)

    def __unicode__(self):
        return u"{} - {} - {}".format(self.child, self.course.short_name)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()
