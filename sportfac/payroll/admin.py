# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Function


@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "rate", "rate_mode")
