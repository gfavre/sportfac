# -*- coding: utf-8 -*-
from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from .models import Registration, Child


class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'status')
    list_filter = ('status', 'course__activity__name')
    search_fields = (
        'child__first_name', 'child__last_name', 'course__activity__number',
        'course__activity__name', 'course__number',
    )
    change_list_template = "admin/change_list_filter_sidebar.html"
    change_list_filter_template = "admin/filter_listing.html"

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
    list_display = ('first_name', 'last_name', 'family', 'school_year')

admin.site.register(Child, ChildAdmin)