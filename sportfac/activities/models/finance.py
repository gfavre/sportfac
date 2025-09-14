import uuid
from datetime import datetime
from datetime import time
from decimal import Decimal

from django.db import models
from django.db.models.aggregates import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from model_utils import Choices

from sportfac.models import TimeStampedModel


RATE_MODES = Choices(("day", _("Daily")), ("hour", _("Hourly")))


class AllocationAccount(TimeStampedModel):
    account = models.CharField(
        max_length=50,
        verbose_name=_("Account"),
        help_text=_("e.g. 154.4652.00"),
        unique=True,
    )
    name = models.CharField(
        max_length=50,
        verbose_name=_("Name"),
        blank=True,
        help_text=_("Some text to help humans filter account numbers"),
    )

    class Meta:
        ordering = ["account"]
        verbose_name = _("Allocation account")
        verbose_name_plural = _("Allocation accounts")

    def __str__(self):
        if self.name:
            return f"{self.account} {self.name}"
        return self.account

    def get_backend_url(self):
        return reverse("backend:allocation-update", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("backend:allocation-update", kwargs={"pk": self.pk})

    def get_delete_url(self):
        return reverse("backend:allocation-delete", kwargs={"pk": self.pk})

    def get_registrations(self, start=None, end=None, **kwargs):
        if start:
            kwargs["created__gte"] = start
        if end:
            kwargs["created__lte"] = datetime.combine(end, time.max)
        return (
            (self.registrations.filter(**kwargs).prefetch_related("bill__datatrans_transactions"))
            .select_related("course", "course__activity", "bill")
            .order_by("created")
        )

    def get_total_transactions(self, period_start=None, period_end=None):
        return self.registrations.all().aggregate(Sum("price"))["price__sum"]


class PaySlip(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instructor = models.ForeignKey("profiles.FamilyUser", verbose_name=_("Instructor"), on_delete=models.CASCADE)
    course = models.ForeignKey("Course", verbose_name=_("Course"), on_delete=models.CASCADE)
    rate = models.DecimalField(_("Rate"), max_digits=6, decimal_places=2)
    rate_mode = models.CharField(_("Rate mode"), max_length=10, choices=RATE_MODES, default=RATE_MODES.hour)
    start_date = models.DateField(_("Start date"))
    end_date = models.DateField(_("End date"))
    function = models.CharField(_("Function"), max_length=255)

    class Meta:
        # Let's see this another time and save too often...
        # unique_together = ('instructor', 'course')
        ordering = ("-created",)

    @property
    def amount(self):
        if self.rate_mode == RATE_MODES.hour:
            duration = self.course.duration
            hours = Decimal(duration.seconds / 3600.0 + duration.days * 24)
            return Decimal(self.rate) * Decimal(self.sessions.count()) * hours
        return Decimal(self.sessions.count()) * self.rate

    @property
    def average_presentees(self):
        return round(float(self.total_presentees) / max(len(self.sessions), 1), 1)

    @property
    def sessions(self):
        return self.course.sessions.filter(
            instructor=self.instructor, date__gte=self.start_date, date__lte=self.end_date
        )

    @property
    def total_presentees(self):
        return sum([session.presentees_nb() for session in self.sessions])

    def get_absolute_url(self):
        return reverse("activities:payslip-detail", kwargs={"pk": self.pk})
