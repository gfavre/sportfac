# -*- coding: utf-8 -*-
from django.db import models
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage

from ckeditor.widgets import CKEditorWidget
from import_export.admin import ImportExportModelAdmin

from registrations.models import Registration
from sportfac.admin_utils import SportfacModelAdmin, SportfacAdminMixin
from .models import Activity, Course, ExtraNeed
from .resources import CourseResource


class ExtraInline(admin.StackedInline):
    model = Course.extra.through
    extra = 0

    verbose_name = _("Extra need")
    verbose_name_plural = _("Extra needs")


class CourseInline(admin.StackedInline):
    model = Course
    extra = 1
    fieldsets = (
        (None, {'fields': ('number', 'price', 'number_of_sessions', 'place', 'uptodate')}),
        (_("Dates"), {'fields': ('start_date', 'end_date', 'day', 'start_time', 'end_time')}),
        (_("Limitations"), {'fields': ('min_participants', 'max_participants', 'schoolyear_min', 'schoolyear_max')}),
        (None, {'fields': ('extra',)}),
    )
    ordering = ['start_date', 'start_time']
    verbose_name = _("course")
    verbose_name_plural = _("courses")


class ActivityAdmin(SportfacModelAdmin):
    list_display = ('number', 'name')
    inlines = [CourseInline]

    verbose_name = _("activity")
    verbose_name_plural = _("activities")
    ordering = ('number', 'name',)


admin.site.register(Activity, ActivityAdmin)


@admin.register(ExtraNeed)
class ExtraNeedAdmin(SportfacModelAdmin):
    pass


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


@admin.register(Course)
class CoursesAdmin(SportfacAdminMixin, ImportExportModelAdmin):
    list_display = (
        'activity', 'number', 'day', 'start_date', 'start_time', 'duration', 'number_of_participants', 'uptodate',
    )
    verbose_name = _("course")
    verbose_name_plural = _("courses")

    ordering = ('number', 'activity__number', 'activity__name', 'start_date', 'start_time')
    list_filter = (ParticipantsListFilter, 'uptodate',)
    change_list_filter_template = "admin/filter_listing.html"
    save_as = True
    inlines = (ExtraInline,)

    resource_class = CourseResource

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


class FlatPageCustom(SportfacAdminMixin, FlatPageAdmin):
    fieldsets = (
        (None, {'fields': ('url', 'title', 'content', 'sites')}),
        (_('Advanced options'), {
            'classes': ('collapse',),
            'fields': (
                'enable_comments',
                'registration_required',
                'template_name',
            ),
        }),
    )

    formfield_overrides = {
        models.TextField: {'widget': CKEditorWidget}
    }


admin.site.unregister(FlatPage)
admin.site.register(FlatPage, FlatPageCustom)
