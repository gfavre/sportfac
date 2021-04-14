# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from sportfac.admin_utils import SportfacModelAdmin

from .models import DatatransTransaction


@admin.register(DatatransTransaction)
class DatatransTransactionAdmin(SportfacModelAdmin):
    date_hierarchy = 'created'
    list_display = ('transaction_id', 'invoice', 'status', 'expiration')
    search_fields = ('transaction_id', 'invoice__billing_identifier',
                     'invoice__family__last_name', 'invoice__family__first_name',
                     'invoice__family__children__last_name', 'invoice__family__children__first_name')
    list_filter = ('status', )
