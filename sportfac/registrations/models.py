# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime, date

from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel

from sportfac.models import TimeStampedModel



class RegistrationManager(models.Manager):
    def get_queryset(self):
        return super(RegistrationManager, self).get_queryset().exclude(status=Registration.STATUS.canceled)

    def all_with_deleted(self):
        return super(RegistrationManager, self).get_queryset().all()

    def waiting(self):
        return self.get_queryset().filter(status=Registration.STATUS.waiting)

    def validated(self):
        return self.get_queryset().filter(status__in=(Registration.STATUS.valid, Registration.STATUS.confirmed))


class Registration(TimeStampedModel, StatusModel):
    STATUS = Choices(('waiting', _("Waiting parent's confirmation")),
                     ('valid', _("Validated by parent")),
                     ('canceled', _("Canceled by administrator")),
                     ('confirmed', _("Confirmed by administrator")),
                     )
    course = models.ForeignKey('activities.Course', related_name="participants", 
                               verbose_name=_("Course"))
    child = models.ForeignKey('profiles.Child', related_name="registrations")

    objects = RegistrationManager()

    class Meta:
        unique_together = ('course', 'child')
        verbose_name = _("Registration")
        verbose_name_plural = _("Registrations")
        ordering = ('child__last_name', 'child__first_name', 'course__start_date')

    @property
    def extra_needs(self):
        return self.course.activity.extra.all().exclude(id__in=self.extra_infos.values_list('key'))  

    def is_valid(self):
        return self.extra_needs.count() == 0

    def __unicode__(self):
        return _(u'%(child)s ⇒ course %(number)s (%(activity)s)') % {'child': unicode(self.child), 
                                                                      'number': self.course.number,
                                                                      'activity': self.course.activity.name}

    def set_waiting(self):
        self.status = self.STATUS.waiting

    def set_valid(self):
        self.status = self.STATUS.valid

    def set_confirmed(self):
        self.status = self.STATUS.confirmed

    def cancel(self):
        self.status = self.STATUS.canceled 

    def overlap(self, r2):
        "Test if another registration object overlaps with this one."  
        # no overlap if course are not the same day
        if self.course.day != r2.course.day:
            return False

        same_days = min(self.course.end_date - r2.course.start_date, 
                        r2.course.end_date - self.course.start_date).days + 1

        # no overlap if periods do not superpose
        if not same_days > 0:
            return False
        # two children can attend same course
        if self.course == r2.course and self.child != r2.child:
            return False

        interval = min(datetime.combine(date.today(), self.course.start_time) - 
                       datetime.combine(date.today(), r2.course.end_time), 
                       datetime.combine(date.today(), r2.course.start_time) - 
                       datetime.combine(date.today(), self.course.end_time))

        if interval.days < 0:
            # overlap
            return True
        elif interval.seconds < (60*30):
            # less than half an hour between courses
            return True
        return False   

    def get_delete_url(self):
        return reverse('backend:registration-delete', kwargs={'pk': self.pk})

    def get_update_url(self):
        return reverse('backend:registration-update', kwargs={'pk': self.pk})


class ExtraInfo(models.Model):
    registration = models.ForeignKey('registrations.Registration', related_name='extra_infos')
    key =  models.ForeignKey('activities.ExtraNeed')
    value = models.CharField(max_length=255)