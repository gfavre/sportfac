from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Appointment, AppointmentSlot, AppointmentType, Rental


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ("formatted_start", "formatted_end", "places", "appointment_type")
    ordering = ("start", "end")

    @admin.display(
        description=_("Start"),
        ordering="start",
    )
    def formatted_start(self, obj):
        return timezone.localtime(obj.start).strftime("%d.%m.%Y %H:%M")

    @admin.display(
        description=_("End"),
        ordering="end",
    )
    def formatted_end(self, obj):
        return timezone.localtime(obj.end).strftime("%d.%m.%Y %H:%M")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("slot", "child", "created", "modified")
    raw_id_fields = ("slot", "child", "family")
    search_fields = (
        "child__first_name",
        "child__last_name",
        "child__id_lagapeo",
        "child__family__first_name",
        "child__family__last_name",
    )
    date_hierarchy = "slot__start"
    list_filter = ("appointment_type",)


@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    list_display = ("label", "formatted_start", "formatted_end")
    ordering = ("start", "end")

    @admin.display(
        description=_("Start"),
        ordering="start",
    )
    def formatted_start(self, obj):
        return obj.start.strftime("%d.%m.%Y %H:%M")

    @admin.display(
        description=_("End"),
        ordering="end",
    )
    def formatted_end(self, obj):
        return obj.end.strftime("%d.%m.%Y %H:%M")


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ("child", "pickup_appointment", "return_appointment", "created", "modified")
    raw_id_fields = ("child", "invoice", "pickup_appointment", "return_appointment")
    search_fields = (
        "child__first_name",
        "child__last_name",
        "child__id_lagapeo",
        "child__family__first_name",
        "child__family__last_name",
    )
    date_hierarchy = "pickup_appointment__slot__start"
