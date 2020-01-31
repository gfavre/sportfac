from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel

from sportfac.models import TimeStampedModel


class Absence(StatusModel, TimeStampedModel):
    STATUS = Choices(
        ('present', _("Present")),
        ('absent', _("Absent")),
        ('excused', _("Excused")),
        ('medical', _("Medical certificate")),
        ('late', _("Late arrival")),
        ('na', _("n/a")),
    )

    child = models.ForeignKey('registrations.Child', on_delete=models.CASCADE)
    session = models.ForeignKey('Session', related_name="absences", on_delete=models.CASCADE)
    notification_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ('child', 'session')

    def __unicode__(self):
        return u"{} - {} - {} - {}".format(self.child, self.session.course.short_name,
                                           self.session.date.isoformat(), self.status)


class Session(TimeStampedModel):
    course = models.ForeignKey('activities.Course', related_name="sessions",)
    activity = models.ForeignKey('activities.Activity', related_name="sessions", null=True)

    date = models.DateField()
    instructor = models.ForeignKey('profiles.FamilyUser', related_name="sessions", null=True)

    def absentees(self):
        return [absence.child for absence in self.absences.exclude(status__in=(Absence.STATUS.present,
                                                                               Absence.STATUS.na,
                                                                               Absence.STATUS.late))]

    def get_absence_for_child(self, child):
        absences = [absence for absence in self.absences.all() if absence.child == child]
        if absences:
            return absences[0]
        else:
            return None

    def __unicode__(self):
        return '%s - %s' % (self.course.short_name, self.date)

    def get_api_url(self):
        return reverse('api:session-detail', kwargs={'pk': self.pk})

    def presentees_nb(self):
        return self.absences.filter(status__in=(Absence.STATUS.present, Absence.STATUS.late)).count()

    def fill_absences(self):
        for registration in self.course.participants.all():
            Absence.objects.get_or_create(
                child=registration.child, session=self,
                defaults={
                    'status': Absence.STATUS.present
                }
            )

    def update_courses_dates(self):
        if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES:
            for course in self.activity.courses.all():
                course.update_dates_from_sessions()
        else:
            self.course.update_dates_from_sessions()

    class Meta:
        ordering = ('date', 'course')
        unique_together = (('date', 'course'),)

