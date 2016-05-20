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
    course = models.ForeignKey('activities.Course')
    date = models.DateTimeField()