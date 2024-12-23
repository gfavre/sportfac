from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from model_utils.models import TimeStampedModel
from phonenumber_field.modelfields import PhoneNumberField


class AppointmentType(TimeStampedModel):
    label = models.CharField(max_length=50, verbose_name=_("Displayed name"))
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ("start", "end")
        verbose_name = _("Appointment type")
        verbose_name_plural = _("Appointment types")

    def __str__(self):
        return self.label


class AppointmentSlot(TimeStampedModel):
    places = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    start = models.DateTimeField()
    end = models.DateTimeField()

    class Meta:
        ordering = ("start", "end")
        verbose_name = _("Appointment slot")
        verbose_name_plural = _("Appointment slots")

    @property
    def available_places(self):
        if hasattr(self, "appointments"):
            return self.places - self.appointments.count()
        return self.places

    @property
    def api_register_url(self):
        return reverse("api:register_slots", kwargs={"slot_id": self.id})

    @property
    def api_management_url(self):
        return reverse("api:slots-detail", kwargs={"pk": self.id})

    @property
    def appointment_type(self):
        return AppointmentType.objects.filter(start__lte=self.start, end__gte=self.end).first()

    def __str__(self):
        local_start = timezone.localtime(self.start)
        local_end = timezone.localtime(self.end)
        if local_start.day == local_end.day:
            return local_start.strftime("%d.%m.%Y, %H:%M-") + local_end.strftime("%H:%M")
        return local_start.strftime("%d.%m.%Y %H:%M") + " - " + local_end.strftime("%d.%m.%Y %H:%M")


class Appointment(TimeStampedModel):
    slot = models.ForeignKey(
        "AppointmentSlot", verbose_name=_("Appointment slot"), on_delete=models.CASCADE, related_name="appointments"
    )
    child = models.ForeignKey(
        "registrations.Child", verbose_name=_("Child"), on_delete=models.CASCADE, related_name="appointment"
    )
    family = models.ForeignKey(
        "profiles.FamilyUser",
        verbose_name=_("Family"),
        null=True,
        on_delete=models.SET_NULL,
        related_name="appointments",
        blank=True,
    )
    email = models.CharField(_("Email"), blank=True, null=True, max_length=255)
    phone_number = PhoneNumberField(_("Phone number"), max_length=30, blank=True)
    appointment_type = models.ForeignKey(
        "AppointmentType", verbose_name=_("Appointment type"), null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _("Appointment")
        verbose_name_plural = _("Appointments")
        ordering = ("slot__start", "slot__end")

    @property
    def get_backend_delete_url(self):
        return reverse("backend:appointment-delete", kwargs={"appointment": self.pk})

    def save(self, *args, **kwargs):
        if self.child and not self.family:
            self.family = self.child.family
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} - {}".format(self.child, self.slot.start.strftime("%d.%m.%Y - %Hh%M"))
