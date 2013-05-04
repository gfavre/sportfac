from django.contrib import admin

from .models import Activity

class ActivityAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}

 admin.site.register(Activity, ActivityAdmin)