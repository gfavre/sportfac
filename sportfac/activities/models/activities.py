from autoslug import AutoSlugField
from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.db import models
from django.db.models.aggregates import Count
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from sportfac.models import TimeStampedModel


class ActivityManager(models.Manager):
    def visible(self):
        return self.get_queryset().filter(courses__visible=True).annotate(count=Count("courses")).filter(count__gt=0)


class Activity(TimeStampedModel):
    """
    An activity
    """

    name = models.CharField(max_length=50, db_index=True, unique=True, verbose_name=_("Name"))
    type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name=_("Type"),
        choices=settings.KEPCHUP_ACTIVITY_TYPES,
        default=settings.KEPCHUP_ACTIVITY_TYPES[0][0],
    )
    number = models.CharField(
        max_length=30,
        db_index=True,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Identifier"),
    )
    slug = AutoSlugField(
        populate_from="name",
        max_length=50,
        db_index=True,
        unique=True,
        help_text=_("Part of the url. Cannot contain punctuation, spaces or accentuated letters"),
    )
    informations = RichTextUploadingField(
        verbose_name=_("Informations"),
        blank=True,
        help_text=_("Specific informations like outfit."),
    )
    description = RichTextUploadingField(verbose_name=_("Description"), blank=True)
    allocation_account = models.ForeignKey(
        "AllocationAccount",
        null=True,
        blank=True,
        related_name="activities",
        verbose_name=_("Allocation account"),
        on_delete=models.SET_NULL,
    )

    managers = models.ManyToManyField(
        "profiles.FamilyUser",
        verbose_name=_("Managers"),
        related_name="managed_activities",
        blank=True,
    )

    objects = ActivityManager()

    class Meta:
        ordering = ["name"]
        verbose_name = _("activity")
        verbose_name_plural = _("activities")

    @property
    def backend_absences_url(self):
        return reverse("backend:activity-absences", kwargs={"activity": self.slug})

    @property
    def backend_url(self):
        return self.get_backend_url()

    @property
    def delete_url(self):
        return self.get_delete_url()

    @property
    def participants(self):
        from registrations.models import Registration

        return Registration.objects.filter(course__in=self.courses.all())

    @property
    def update_url(self):
        return self.get_update_url()

    def get_absolute_url(self):
        return reverse("activities:activity-detail", kwargs={"slug": self.slug})

    def get_backend_url(self):
        return reverse("backend:activity-detail", kwargs={"activity": self.slug})

    def get_delete_url(self):
        return reverse("backend:activity-delete", kwargs={"activity": self.slug})

    def get_update_url(self):
        return reverse("backend:activity-update", kwargs={"activity": self.slug})

    def __str__(self):
        return self.name
