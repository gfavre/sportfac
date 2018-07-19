from django.contrib import admin

from .models import Building, Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'years_label', 'number')
    list_filter = ('years',)
    filter_horizontal = ('years',)
    change_list_filter_template = "admin/filter_listing.html"


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'city',)
