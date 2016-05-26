from __future__ import unicode_literals
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel

from sportfac.models import TimeStampedModel


class Absence(StatusModel, TimeStampedModel):
    STATUS = Choices(('absent', _("Absent")),
                     ('excused', _("Excused")),
                     ('late', _("Late arrival"))
                    )

    child = models.ForeignKey('registrations.Child')
    session = models.ForeignKey('Session', related_name="absences")


class Session(TimeStampedModel):
    course = models.ForeignKey('activities.Course', related_name="sessions")
    date = models.DateField()

    def absentees(self):
        return [absence.child for absence in self.absences.all()]
    
    def __unicode__(self):
        return '%s - %s' % (self.course.short_name, self.date)
    
    class Meta:
        ordering = ('date', 'course')

