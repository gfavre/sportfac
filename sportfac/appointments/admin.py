# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from .models import AppointmentSlot, Appointment


@admin.register(AppointmentSlot)
class AppointmentSlotAdmin(admin.ModelAdmin):
    pass


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('slot', 'child')
