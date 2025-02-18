from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_tenants.models import DomainMixin, TenantMixin
from dynamic_preferences.models import PerInstancePreferenceModel
from model_utils import Choices


class YearTenant(TenantMixin):
    STATUS = Choices(
        ("creating", _("Creating period")),
        ("copying", _("Copying data from previous year")),
        ("ready", _("Ready to use")),
    )

    status = models.CharField(choices=STATUS, default=STATUS.creating, max_length=20)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)
    created_on = models.DateTimeField(auto_now_add=True)

    auto_create_schema = False

    class Meta:
        ordering = ("start_date",)

    def __str__(self):
        if self.start_date.year != self.end_date.year:
            return "%i-%i" % (self.start_date.year, self.end_date.year)
        return "%i.%i-%i.%i %i" % (
            self.start_date.day,
            self.start_date.month,
            self.end_date.day,
            self.end_date.month,
            self.end_date.year,
        )

    @property
    def is_production(self):
        return self.domains.first().is_current

    @property
    def is_past(self):
        return self.end_date < timezone.now().date()

    @property
    def is_future(self):
        return self.start_date > timezone.now().date()

    @property
    def is_ready(self):
        return self.status == self.STATUS.ready

    def get_delete_url(self):
        return reverse("backend:year-delete", kwargs={"pk": self.pk})

    def get_update_url(self):
        return reverse("backend:year-update", kwargs={"pk": self.pk})


class Domain(DomainMixin):
    is_current = models.BooleanField(default=False)

    def __str__(self):
        if self.is_current:
            return "[default domain] " + self.domain
        return self.domain


class TenantPreferenceModel(PerInstancePreferenceModel):
    instance = models.ForeignKey("backend.YearTenant", on_delete=models.deletion.CASCADE)

    class Meta(PerInstancePreferenceModel.Meta):
        verbose_name = _("tenant preference")
        verbose_name_plural = _("tenant preferences")
        app_label = "backend"
        abstract = False
