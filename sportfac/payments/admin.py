from django.contrib import admin
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _

from sportfac.admin_utils import SportfacModelAdmin
from .models import DatatransTransaction, PostfinanceTransaction


@admin.register(DatatransTransaction)
class DatatransTransactionAdmin(SportfacModelAdmin):
    date_hierarchy = "created"
    list_display = ("transaction_id", "get_invoice_identifier", "status", "expiration", "created", "modified")
    search_fields = (
        "transaction_id",
        "invoice__billing_identifier",
        "invoice__family__last_name",
        "invoice__family__first_name",
        "invoice__family__children__last_name",
        "invoice__family__children__first_name",
    )
    list_filter = ("status",)

    @admin.display(description=_("Invoice"))
    def get_invoice_identifier(self, obj):
        url = reverse("admin:registrations_bill_change", args=(obj.invoice.id,))
        return mark_safe(f'<a href="{url}">{obj.invoice.billing_identifier}</a>')


@admin.register(PostfinanceTransaction)
class PostfinanceTransactionAdmin(SportfacModelAdmin):
    date_hierarchy = "created"
    list_display = ("transaction_id", "get_invoice_identifier", "status", "created", "modified")
    search_fields = (
        "transaction_id",
        "invoice__billing_identifier",
        "invoice__family__last_name",
        "invoice__family__first_name",
        "invoice__family__children__last_name",
        "invoice__family__children__first_name",
    )
    list_filter = ("status",)

    @admin.display(description=_("Invoice"))
    def get_invoice_identifier(self, obj):
        url = reverse("admin:registrations_bill_change", args=(obj.invoice.id,))
        return mark_safe(f'<a href="{url}">{obj.invoice.billing_identifier}</a>')
