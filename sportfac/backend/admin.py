from __future__ import absolute_import

from django.contrib import admin
from django.db import connection

from sportfac.admin_utils import SportfacAdminMixin, SportfacModelAdmin

from .models import Domain, YearTenant


@admin.register(YearTenant)
class TenantAdmin(SportfacModelAdmin):
    list_display = ("__unicode__", "start_date", "end_date", "status")

    def save_model(self, request, obj, form, change):
        connection.set_schema_to_public()
        return super(TenantAdmin, self).save_model(request, obj, form, change)


@admin.register(Domain)
class DomainAdmin(SportfacModelAdmin):
    pass


from dbtemplates.admin import TemplateAdmin
from dbtemplates.models import Template


admin.site.unregister(Template)


@admin.register(Template)
class SportfacTemplateAdmin(SportfacAdminMixin, TemplateAdmin):
    pass


from dynamic_preferences.admin import GlobalPreferenceAdmin
from dynamic_preferences.models import GlobalPreferenceModel


admin.site.unregister(GlobalPreferenceModel)


@admin.register(GlobalPreferenceModel)
class SportfacGlobalPreferenceAdmin(SportfacAdminMixin, GlobalPreferenceAdmin):
    pass


from django.contrib.sites.admin import SiteAdmin
from django.contrib.sites.models import Site


admin.site.unregister(Site)


@admin.register(Site)
class SportfacSiteAdmin(SportfacAdminMixin, SiteAdmin):
    pass
