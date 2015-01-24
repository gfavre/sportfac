# -*- coding: utf-8 -*-
from django.contrib import admin
from .models import MailArchive


class MailArchiveAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'subject',
        'admin_recipients',
        'admin_message',
        'created',
        'template',
    )
    list_filter = ('created', 'template')
        
admin.site.register(MailArchive, MailArchiveAdmin)
