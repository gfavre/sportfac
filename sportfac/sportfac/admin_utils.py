# -*- coding: utf-8 -*-
from django.contrib import admin


class SportfacAdminMixin:
    def log_addition(self, *args, **kwargs):
        pass

    def log_change(self, *args, **kwargs):
        pass

    def log_deletion(self, *args, **kwargs):
        pass


class SportfacModelAdmin(SportfacAdminMixin, admin.ModelAdmin):
    def log_addition(self, *args, **kwargs):
        pass

    def log_change(self, *args, **kwargs):
        pass

    def log_deletion(self, *args, **kwargs):
        pass
