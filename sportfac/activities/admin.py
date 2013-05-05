from django.contrib import admin
from django.utils.translation import ugettext as _

from .models import Activity, Responsible, Course

class CourseInline(admin.TabularInline):
    model = Course
    extra = 1
    fieldsets = (
       (None, {'fields': ('responsible', 'price', 'number_of_sessions')}),
       (_("Dates"), {'fields': ('start_date', 'end_date', 'day', 'start_time', 'end_time')}),
       (_("Limitations"), {'fields': ('min_participants', 'max_participants', 'schoolyear_min', 'schoolyear_max')}),
    )
    ordering=['start_date',]
    verbose_name = _("course")
    verbose_name_plural = _("courses")

class ActivityAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CourseInline,]

admin.site.register(Activity, ActivityAdmin)


class ResponsibleAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')

admin.site.register(Responsible, ResponsibleAdmin)

 
