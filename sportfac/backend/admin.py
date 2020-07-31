from django.contrib import admin
from django.db import connection

from .models import YearTenant, Domain
from sportfac.admin_utils import SportfacModelAdmin, SportfacAdminMixin


@admin.register(YearTenant)
class TenantAdmin(SportfacModelAdmin):
    list_display = ('__unicode__', 'start_date', 'end_date', 'status')
    
    def save_model(self, request, obj, form, change):
        connection.set_schema_to_public()
        return super(TenantAdmin, self).save_model(request, obj, form, change)


@admin.register(Domain)
class DomainAdmin(SportfacModelAdmin):
    pass


from dbtemplates.models import Template
from dbtemplates.admin import TemplateAdmin
admin.site.unregister(Template)


@admin.register(Template)
class SportfacTemplateAdmin(SportfacAdminMixin, TemplateAdmin):
    pass


from dynamic_preferences.models import GlobalPreferenceModel
from dynamic_preferences.admin import GlobalPreferenceAdmin
admin.site.unregister(GlobalPreferenceModel)


@admin.register(GlobalPreferenceModel)
class SportfacGlobalPreferenceAdmin(SportfacAdminMixin, GlobalPreferenceAdmin):
    pass
