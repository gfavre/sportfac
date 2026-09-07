from django.contrib import admin

from sportfac.admin_utils import SportfacModelAdmin

from .models import Function


@admin.register(Function)
class FunctionAdmin(SportfacModelAdmin):
    list_display = ("code", "name", "rate", "rate_mode")
