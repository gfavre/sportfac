from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from sportfac.admin_utils import SportfacModelAdmin

from .models import WizardStep


@admin.register(WizardStep)
class WizardStepAdmin(SortableAdminMixin, SportfacModelAdmin):
    list_display = (
        "slug",
        "title",
        "position",
    )
    list_display_links = ("slug",)
