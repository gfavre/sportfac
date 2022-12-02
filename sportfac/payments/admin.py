# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.contrib import admin
from django.urls import reverse
from django.utils.text import mark_safe
from django.utils.translation import ugettext_lazy as _

from sportfac.admin_utils import SportfacModelAdmin
from .models import DatatransTransaction


@admin.register(DatatransTransaction)
class DatatransTransactionAdmin(SportfacModelAdmin):
    date_hierarchy = 'created'
    list_display = ('transaction_id', 'get_invoice_identifier', 'status', 'expiration')
    search_fields = ('transaction_id', 'invoice__billing_identifier',
                     'invoice__family__last_name', 'invoice__family__first_name',
                     'invoice__family__children__last_name', 'invoice__family__children__first_name')
    list_filter = ('status', )

    def get_invoice_identifier(self, obj):
        url = reverse('admin:registrations_bill_change', args=(obj.invoice.id,))
        return mark_safe('<a href="{}">{}</a>'.format(url, obj.invoice.billing_identifier))
    get_invoice_identifier.short_description = _('Invoice')
