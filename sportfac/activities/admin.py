from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Activity, Responsible, Course

class CourseInline(admin.StackedInline):
    model = Course
    extra = 1
    fieldsets = (
       (None, {'fields': ('responsible', 'price', 'number_of_sessions', 'place')}),
       (_("Dates"), {'fields': ('start_date', 'end_date', 'day', 'start_time', 'end_time')}),
       (_("Limitations"), {'fields': ('min_participants', 'max_participants', 'schoolyear_min', 'schoolyear_max')}),
    )
    ordering=['start_date', 'start_time']
    verbose_name = _("course")
    verbose_name_plural = _("courses")

class ActivityAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CourseInline,]
    verbose_name = _("activity")
    verbose_name_plural = _("activities")
    ordering = ('name',)
    

admin.site.register(Activity, ActivityAdmin)


class ResponsibleAdmin(admin.ModelAdmin):
    list_display = ('fullname', 'phone', 'email')
    verbose_name = _("responsible")
    verbose_name_plural = _("responsibles")
    ordering = ('last', 'first')

admin.site.register(Responsible, ResponsibleAdmin)

 
