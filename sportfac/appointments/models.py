from decimal import Decimal

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


class AppointmentSlotManager(models.Manager):
    def with_available_places(self):
        return self.annotate(count_available_places=models.F("places") - models.Count("appointments"))


class AppointmentSlot(TimeStampedModel):
    APPOINTMENT_TYPES = (
        ("pickup", _("Pickup")),
        ("return", _("Return")),
        ("other", _("Other")),
    )
    places = models.PositiveSmallIntegerField(verbose_name=_("Maximal number of participants"))
    start = models.DateTimeField()
    end = models.DateTimeField()
    appointment_type = models.CharField(choices=APPOINTMENT_TYPES, max_length=10, default=APPOINTMENT_TYPES[0][0])

    objects = AppointmentSlotManager()

    class Meta:
        ordering = ("start", "end")
        verbose_name = _("Appointment slot")
        verbose_name_plural = _("Appointment slots")

    @property
    def available_places(self):
        if hasattr(self, "count_available_places"):
            return self.count_available_places
        if hasattr(self, "appointments"):
            return self.places - self.appointments.count()
        return self.places

    @property
    def api_register_url(self):
        return reverse("api:register_slots", kwargs={"slot_id": self.id})

    @property
    def api_management_url(self):
        return reverse("api:slots-detail", kwargs={"pk": self.id})

    def __str__(self):
        local_start = timezone.localtime(self.start)
        local_end = timezone.localtime(self.end)
        places_str = ""
        if self.places:
            places_str = _(" - %(remaining_places)d remaining places") % {"remaining_places": self.available_places}
        if local_start.day == local_end.day:
            return local_start.strftime("%d.%m.%Y, %H:%M-") + local_end.strftime("%H:%M") + places_str
        return local_start.strftime("%d.%m.%Y %H:%M") + " - " + local_end.strftime("%d.%m.%Y %H:%M") + places_str


class Rental(TimeStampedModel):
    child = models.ForeignKey(
        "registrations.Child", verbose_name=_("Child"), on_delete=models.CASCADE, related_name="rentals"
    )
    invoice = models.ForeignKey(
        "registrations.Bill",
        verbose_name=_("Invoice"),
        on_delete=models.SET_NULL,
        related_name="rentals",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(_("Amount"), max_digits=6, decimal_places=2, default=Decimal(0.0))
    paid = models.BooleanField(_("Paid"), default=False)
    pickup_appointment = models.OneToOneField(
        "Appointment",
        verbose_name=_("Pickup slot"),
        on_delete=models.SET_NULL,
        related_name="pickup_rental",
        null=True,
        blank=True,
    )
    return_appointment = models.OneToOneField(
        "Appointment",
        verbose_name=_("Return slot"),
        on_delete=models.SET_NULL,
        related_name="return_rental",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Rental")
        verbose_name_plural = _("Rentals")
        ordering = ("child",)

    def delete(self, using=None, keep_parents=False):
        if self.pickup_appointment:
            self.pickup_appointment.delete()
        if self.return_appointment:
            self.return_appointment.delete()
        super().delete(using, keep_parents)

    def __str__(self):
        return f"{self.child}"


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

    @property
    def get_backend_edit_url(self):
        return reverse("backend:appointment-update", kwargs={"appointment": self.pk})

    def save(self, *args, **kwargs):
        if self.child and not self.family:
            self.family = self.child.family
        super().save(*args, **kwargs)

    def __str__(self):
        return "{} - {}".format(self.child, self.slot.start.strftime("%d.%m.%Y - %Hh%M"))
