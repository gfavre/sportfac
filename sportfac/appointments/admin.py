# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Appointment, AppointmentSlot


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    pass


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("slot", "child")
