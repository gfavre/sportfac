# -*- coding: utf-8 -*-
from django.contrib import admin

from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin

from sportfac.admin_utils import SportfacModelAdmin, SportfacAdminMixin
from .models import Registration, Child, Bill, ExtraInfo, Transport, RegistrationsProfile


class RegistrationResource(resources.ModelResource):
    course_number = fields.Field('course__number', column_name="Cours")
    course_name = fields.Field('course__name', column_name="Nom affiché du cours")

    child_id = fields.Field('child__id', column_name="Enfant")
    child_id_lagapeo = fields.Field('child__id_lagapeo', column_name="Identifiant SSF (LAGAPEO)")
    child_name = fields.Field(column_name="Nom de l'enfant")

    before_level = fields.Field('before_level', column_name='Niveau - 1')
    after_level = fields.Field('after_level', column_name='Niveau + 1')

    class Meta:
        model = Registration
        fields = ('id', 'course_number', 'course_name',
                  'child_id', 'child_id_lagapeo', 'child_name',
                  'before_level', 'after_level', 'note')
        export_order = ('id', 'course_number', 'course_name',
                        'child_id', 'child_id_lagapeo', 'child_name',
                        'before_level', 'after_level', 'note')

    def dehydrate_child_name(self, registration):
        return registration.child.full_name


@admin.register(ExtraInfo)
class ExtraInfoAdmin(SportfacModelAdmin):
    list_display = ('registration', 'key', 'value')
    search_fields = ('registration__child__first_name',
                     'registration__child__last_name',
                     'registration__course__activity__name',
                     'registration__course__number',
                     'key__question_label', 'value')
    list_filter = ('key',)
    raw_id_fields = ('registration', )


class ExtraInfoInline(admin.StackedInline):
    model = ExtraInfo
    extra = 0


@admin.register(Registration)
class RegistrationAdmin(SportfacAdminMixin, ImportExportModelAdmin):
    list_display = ('__unicode__', 'transport', 'status', 'created', 'modified')
    list_filter = ('status', 'transport', 'course__activity__name')
    search_fields = (
        'child__first_name', 'child__last_name', 'course__activity__number',
        'course__activity__name', 'course__number',
    )
    raw_id_fields = ('child', 'course', 'bill')
    date_hierarchy = 'created'
    change_list_filter_template = "admin/filter_listing.html"
    inlines = [ExtraInfoInline]
    actions = ['delete_model', ]
    resource_class = RegistrationResource

    def get_queryset(self, request):
        qs = self.model._default_manager.all_with_deleted()
        return qs.select_related('course', 'course__activity', 'child', 'transport')

    def get_actions(self, request):
        actions = super(RegistrationAdmin, self).get_actions(request)
        del actions['delete_selected']
        return actions


@admin.register(RegistrationsProfile)
class RegistrationsProfileAdmin(SportfacModelAdmin):
    list_display = ('user', 'has_paid_all', 'finished_registering', 'last_registration')
    raw_id_fields = ('user', )
    list_filter = ('has_paid_all', 'finished_registering')


@admin.register(Child)
class ChildAdmin(SportfacModelAdmin):
    list_display = ('first_name', 'last_name', 'family', 'school_year', 'id_lagapeo', 'created', 'modified')
    search_fields = ('first_name', 'last_name', 'id_lagapeo', 'family__first_name', 'family__last_name')
    list_filter = ('school_year', 'status', 'is_blacklisted')
    raw_id_fields = ('family', 'teacher', )


class RegistrationInline(admin.StackedInline):
    model = Registration
    raw_id_fields = ('child', 'course')
    extra = 0


@admin.register(Bill)
class BillAdmin(SportfacModelAdmin):
    list_display = ('billing_identifier', 'total', 'family', 'status', 'created', 'modified', 'reminder_sent')
    list_filter = ('status',)
    raw_id_fields = ('family',)
    date_hierarchy = 'created'
    search_fields = ('billing_identifier', 'family__first_name', 'family__last_name')

    inlines = [RegistrationInline]

    def get_queryset(self, request):
        return super(BillAdmin, self).get_queryset(request).select_related('family')


@admin.register(Transport)
class TransportAdmin(SportfacModelAdmin):
    pass
