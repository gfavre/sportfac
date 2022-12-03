# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.contrib import admin

from .models import Function


@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "rate", "rate_mode")
