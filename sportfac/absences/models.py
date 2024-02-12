from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from model_utils import Choices
from model_utils.models import StatusModel

from sportfac.models import TimeStampedModel


class Absence(StatusModel, TimeStampedModel):
    STATUS = Choices(
        ("present", _("Present")),
        ("absent", _("Absent")),
        ("excused", _("Excused")),
        ("medical", _("Medical certificate")),
        ("late", _("Late arrival")),
        ("canceled", _("Canceled course")),
        ("na", _("n/a")),
    )

    child = models.ForeignKey("registrations.Child", on_delete=models.CASCADE, related_name="absences")
    session = models.ForeignKey("Session", related_name="absences", on_delete=models.CASCADE)
    notification_sent = models.BooleanField(default=False)

    class Meta:
        unique_together = ("child", "session")

    def __str__(self):
        return "{} - {} - {} - {}".format(
            self.child, self.session.course.short_name, self.session.date.isoformat(), self.status
        )


class Session(TimeStampedModel):
    course = models.ForeignKey("activities.Course", related_name="sessions", on_delete=models.CASCADE)
    activity = models.ForeignKey("activities.Activity", related_name="sessions", null=True, on_delete=models.CASCADE)
    date = models.DateField()
    instructor = models.ForeignKey("profiles.FamilyUser", null=True, on_delete=models.SET_NULL)
    export_date = models.DateTimeField(verbose_name=_("Exported to payroll"), null=True, blank=True)

    class Meta:
        ordering = ("date", "course")
        unique_together = (("date", "course"),)

    def absentees(self):
        return [
            absence.child
            for absence in self.absences.exclude(
                status__in=(Absence.STATUS.present, Absence.STATUS.na, Absence.STATUS.late)
            )
        ]

    def fill_absences(self):
        for registration in self.course.participants.all():
            Absence.objects.get_or_create(
                child=registration.child, session=self, defaults={"status": Absence.STATUS.present}
            )

    def get_absence_for_child(self, child):
        absences = [absence for absence in self.absences.all() if absence.child == child]
        if absences:
            return absences[0]
        return None

    def get_api_url(self):
        return reverse("api:session-detail", kwargs={"pk": self.pk})

    def presentees_nb(self):
        return self.absences.filter(status__in=(Absence.STATUS.present, Absence.STATUS.late)).count()

    def update_courses_dates(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            if settings.KEPCHUP_ABSENCES_RELATE_TO_ACTIVITIES and self.activity:
                for course in self.activity.courses.all():
                    course.update_dates_from_sessions()
            else:
                self.course.update_dates_from_sessions()

    def __str__(self):
        return f"{self.course.short_name} - {self.date}"
