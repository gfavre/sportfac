import os

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from sportfac.admin_utils import SportfacModelAdmin

from .models import Attachment, GenericEmail, MailArchive


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("filename", "get_mail", "created")
    list_filter = ("created",)
    raw_id_fields = ("mail",)
    queryset = Attachment.objects.select_related("mail")

    @admin.display(
        description=_("File"),
        ordering="file",
    )
    def filename(self, obj):
        return os.path.basename(obj.file.name) if obj.file else _("No File")

    @admin.display(
        description=_("email"),
        ordering="mail__subject",
    )
    def get_mail(self, obj):
        return obj.mail.subject


class AttachmentInline(admin.TabularInline):  # or admin.StackedInline
    model = Attachment
    extra = 0  # No extra empty forms


@admin.register(MailArchive)
class MailArchiveAdmin(SportfacModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "subject",
        "created",
        "status",
        "template",
    )
    list_filter = ("created", "status")
    inlines = [AttachmentInline]  # Add the inline here


@admin.register(GenericEmail)
class GenericEmailAdmin(SportfacModelAdmin):
    list_display = ("subject", "subject_template", "body_template")
