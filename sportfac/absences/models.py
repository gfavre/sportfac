from __future__ import unicode_literals

from django.db import models

from model_utils.models import StatusModel

from sportfac.models import TimeStampedModel


class Absence(StatusTimeStampedModel)
    STATUS = Choices(('absent', _("Absent")),
                     ('excused', _("Excused")),
                     ('late', _("Late arrival"))
                    )

    child = models.ForeignKey('registrations.Child')
    course = models.ForeignKey('activities.Course')
    date = models.DateTimeField()