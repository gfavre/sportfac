from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Appointment, AppointmentSlot, AppointmentType


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    list_display = ("formatted_start", "formatted_end", "places")
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


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("slot", "child")
    raw_id_fields = ("slot", "child", "family")


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
