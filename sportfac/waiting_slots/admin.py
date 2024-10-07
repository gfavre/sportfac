from django.contrib import admin

from .models import WaitingSlot


@admin.register(WaitingSlot)
class WaitingSlotAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("child", "course", "created")
    list_filter = ("course__activity", "created")
    raw_id_fields = ("child", "course")
    search_fields = (
        "course__activity__name",
        "course__number",
        "child__first_name",
        "child__last_name",
        "child__family__last_name",
    )
    ordering = ("course__activity__name", "course__number", "created")
