from django.contrib import admin
from django.utils.translation import gettext_lazy as _

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
    verbose_name = _("activity")
    verbose_name_plural = _("activities")
    

admin.site.register(Activity, ActivityAdmin)


class ResponsibleAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email')
    verbose_name = _("responsible")
    verbose_name_plural = _("responsibles")


admin.site.register(Responsible, ResponsibleAdmin)

 
