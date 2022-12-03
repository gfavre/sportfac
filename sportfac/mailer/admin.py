# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib import admin

from sportfac.admin_utils import SportfacModelAdmin

from .models import GenericEmail, MailArchive


@admin.register(MailArchive)
class MailArchiveAdmin(SportfacModelAdmin):
    list_display = (
        "id",
        "subject",
        #'admin_recipients',
        "admin_message",
        "created",
        "status",
        "template",
    )
    list_filter = ("created", "template", "status")


@admin.register(GenericEmail)
class GenericEmailAdmin(SportfacModelAdmin):
    list_display = ("subject_template", "body_template")
