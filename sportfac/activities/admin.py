#!/usr/bin/python
# -*- coding: utf-8 -*-

from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from ckeditor.widgets import CKEditorWidget

from registrations.models import Registration
from sportfac.utils import UnicodeWriter
from .models import Activity, Course, ExtraNeed


class CourseInline(admin.StackedInline):
    model = Course
    extra = 1
    fieldsets = (
       (None, {'fields': ('number', 'responsible', 'price', 'number_of_sessions', 'place', 'uptodate')}),
       (_("Dates"), {'fields': ('start_date', 'end_date', 'day', 'start_time', 'end_time')}),
       (_("Limitations"), {'fields': ('min_participants', 'max_participants', 'schoolyear_min', 'schoolyear_max')}),
    )
    ordering=['start_date', 'start_time']
    verbose_name = _("course")
    verbose_name_plural = _("courses")

class ExtraInline(admin.StackedInline):
    model = ExtraNeed
    extra = 0
    
    verbose_name = _("Extra need")
    verbose_name_plural = _("Extra needs")



class ActivityAdmin(admin.ModelAdmin):
    list_display = ('number', 'name')
    inlines = [CourseInline, ExtraInline]
    
    verbose_name = _("activity")
    verbose_name_plural = _("activities")
    ordering = ('number', 'name',)
    

admin.site.register(Activity, ActivityAdmin)


class ParticipantsListFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('number of participants')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'participants'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('min', _('Not reached minimum participants')),
            ('ok', _('Min participants reached')),
            ('max', _('Full')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'min':
            return queryset.filter(participants__count__lt=models.F('min_participants'))
        if self.value() == 'max':
            return queryset.filter(participants__count__gte=models.F('max_participants'))
        elif self.value() == 'ok':
            return queryset.filter(participants__count__lt=models.F('max_participants'),
                                   participants__count__gte=models.F('min_participants'))


class CoursesAdmin(admin.ModelAdmin):
    list_display =('activity', 'number', 'day', 'start_date', 'start_time', 'duration', 'number_of_participants', 'uptodate',)
    verbose_name = _("course")
    verbose_name_plural = _("courses")
    
    ordering = ('number', 'activity__number', 'activity__name', 'start_date', 'start_time')
    list_filter=(ParticipantsListFilter, 'uptodate',)
    change_list_filter_template = "admin/filter_listing.html"
    change_list_template = "admin/change_list_filter_sidebar.html"
    save_as = True
    
    actions = ('export',)
    
    
    def get_queryset(self, request):
        qs = super(CoursesAdmin, self).get_queryset(request)
        qs = qs.annotate(models.Count('participants'))
        return qs
    
    def number_of_participants(self, obj):
        return Registration.objects.filter(course=obj).count()
    number_of_participants.admin_order_field = 'participants__count'
    number_of_participants.short_description = _('number of participants')
    
    def duration(self, obj):
        return obj.duration
    duration.short_description = _("Duration")
    
    
    def export(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=cours.csv'
        writer = UnicodeWriter(response)
        
        field_names = (u'Cours n°',
                       u'Activité',
                       u'Activité n°',
                       u'Responsable',
                       u'Nombre de sessions',
                       u'Jour',
                       u'Durée (minutes)',
                       u'Date de début',
                       u'Heure de début',
                       u'Date de fin',
                       u'Heure de fin',
                       u'Prix',
                       u'Lieu',
                       )
        writer.writerow(field_names)
        for course in queryset.select_related('responsible', 'activity').all():
            writer.writerow((str(course.number),
                             course.activity.name,
                             str(course.activity.number),
                             unicode(course.responsible),
                             str(course.number_of_sessions),
                             course.day_name,
                             str(int(course.duration.total_seconds() / 60)),
                             course.start_date.strftime('%d.%m.%Y'),
                             course.start_time.strftime('%H:%M'),
                             course.end_date.strftime('%d.%m.%Y'),
                             course.end_time.strftime('%H:%M'),
                             str(course.price),
                             course.place,
                             ))
        #wrapped = ("<html><body>", response.content, "</body></html>")
        #return HttpResponse(wrapped)
        return response
    export.short_description = _('Export selected courses')

    
    


admin.site.register(Course, CoursesAdmin)




class FlatPageCustom(FlatPageAdmin):
    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget}
    }


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageCustom)
