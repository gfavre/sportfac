# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.contrib import admin


from .models import Function


@admin.register(Function)
class FunctionAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'rate', 'rate_mode')
