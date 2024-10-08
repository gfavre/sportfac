from django.contrib import admin

from adminsortable2.admin import SortableAdminMixin

from .models import WizardStep


@admin.register(WizardStep)
class WizardStepAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        "slug",
        "title",
        "position",
    )
    list_display_links = ("slug",)
