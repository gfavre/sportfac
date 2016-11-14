# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import Registration, Child, Bill, ExtraInfo


class ExtraInfoAdmin(admin.ModelAdmin):
    list_display = ('registration', 'key', 'value')
    search_fields = ('registration__child__first_name',
                     'registration__child__last_name',
                     'registration__course__activity__name',
                     'registration__course__number',
                     'key__question_label', 'value')
    list_filter = ('key',)

admin.site.register(ExtraInfo, ExtraInfoAdmin)

class ExtraInfoInline(admin.StackedInline):
    model = ExtraInfo
    extra = 0

class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'status', 'created', 'modified')
    list_filter = ('status', 'course__activity__name')
    search_fields = (
        'child__first_name', 'child__last_name', 'course__activity__number',
        'course__activity__name', 'course__number',
    )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"
    inlines = [ExtraInfoInline]
    actions = ['delete_model',]

    def get_queryset(self, request):
        #qs = super(RegistrationAdmin, self).get_queryset(request)
        #return qs 19
        qs = self.model._default_manager.all_with_deleted()
        return qs.select_related('course', 'course__activity', 'child')
    
    def get_actions(self, request):
        actions = super(RegistrationAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions


admin.site.register(Registration, RegistrationAdmin)

class ChildAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'family', 'school_year', 'created', 'modified')

admin.site.register(Child, ChildAdmin)

class BillAdmin(admin.ModelAdmin):
    list_display = ('billing_identifier', 'total', 'family', 'status', 'created', 'modified')
    list_filter = ('status',)

admin.site.register(Bill, BillAdmin)