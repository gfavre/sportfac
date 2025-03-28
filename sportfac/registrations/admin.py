from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin

from appointments.models import Rental
from sportfac.admin_utils import SportfacAdminMixin, SportfacModelAdmin
from .models import (
    Bill,
    Child,
    ChildActivityLevel,
    ExtraInfo,
    Registration,
    RegistrationsProfile,
    RegistrationValidation,
    Transport,
)


class RegistrationResource(resources.ModelResource):
    course_number = fields.Field("course__number", column_name="Cours")
    course_name = fields.Field("course__name", column_name="Nom affiché du cours")

    child_id = fields.Field("child__id", column_name="Enfant")
    child_id_lagapeo = fields.Field("child__id_lagapeo", column_name="Identifiant SSF (LAGAPEO)")
    child_name = fields.Field(column_name="Nom de l'enfant")

    before_level = fields.Field("before_level", column_name="Niveau - 1")
    after_level = fields.Field("after_level", column_name="Niveau + 1")

    class Meta:
        model = Registration
        fields = (
            "id",
            "course_number",
            "course_name",
            "child_id",
            "child_id_lagapeo",
            "child_name",
            "before_level",
            "after_level",
        )
        export_order = (
            "id",
            "course_number",
            "course_name",
            "child_id",
            "child_id_lagapeo",
            "child_name",
            "before_level",
            "after_level",
        )

    def dehydrate_child_name(self, registration):
        return registration.child.full_name


@admin.register(ExtraInfo)
class ExtraInfoAdmin(SportfacModelAdmin):
    list_display = ("registration", "key", "value", "created")
    search_fields = (
        "registration__child__first_name",
        "registration__child__last_name",
        "registration__course__activity__name",
        "registration__course__number",
        "key__question_label",
        "value",
    )
    list_filter = ("key",)
    raw_id_fields = ("registration",)


class ExtraInfoInline(admin.StackedInline):
    model = ExtraInfo
    extra = 0


@admin.register(Registration)
class RegistrationAdmin(SportfacAdminMixin, ImportExportModelAdmin):
    actions = [
        "delete_model",
    ]
    change_list_filter_template = "admin/filter_listing.html"
    date_hierarchy = "created"
    inlines = [ExtraInfoInline]
    list_display = ("__str__", "transport", "status", "created", "modified")
    list_filter = ("status", "transport", "course__activity__name", "cancelation_reason")
    raw_id_fields = ("child", "course", "bill")
    resource_class = RegistrationResource
    search_fields = (
        "child__first_name",
        "child__last_name",
        "course__activity__number",
        "course__activity__name",
        "course__number",
    )

    def get_queryset(self, request):
        qs = self.model._default_manager.all_with_deleted()
        return qs.select_related("course", "course__activity", "child", "transport")


@admin.register(RegistrationsProfile)
class RegistrationsProfileAdmin(SportfacModelAdmin):
    list_display = ("user", "has_paid_all", "finished_registering", "last_registration")
    list_filter = ("has_paid_all", "finished_registering")
    raw_id_fields = ("user",)
    search_fields = (
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("user")


@admin.register(Child)
class ChildAdmin(SportfacModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "first_name",
        "last_name",
        "family",
        "school_year",
        "id_lagapeo",
        "created",
        "modified",
    )
    list_filter = ("school_year", "status", "is_blacklisted")
    raw_id_fields = (
        "family",
        "teacher",
    )
    search_fields = (
        "first_name",
        "last_name",
        "id_lagapeo",
        "family__first_name",
        "family__last_name",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("family").prefetch_related("school_year")


class RegistrationInline(admin.StackedInline):
    model = Registration
    raw_id_fields = ("child", "course")
    extra = 0


class RentalsInline(admin.StackedInline):
    model = Rental
    raw_id_fields = ("child", "pickup_appointment", "return_appointment")
    extra = 0


@admin.register(Bill)
class BillAdmin(SportfacModelAdmin):
    list_display = (
        "billing_identifier",
        "total",
        "get_family",
        "status",
        "created",
        "reminder_sent",
        "payment_method",
    )
    list_filter = ("status", "payment_method")
    raw_id_fields = ("family",)
    date_hierarchy = "created"
    search_fields = ("billing_identifier", "family__first_name", "family__last_name")

    inlines = [RegistrationInline, RentalsInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("family")

    @admin.display(description=_("Family"))
    def get_family(self, obj):
        return mark_safe(
            '<a href="{}">{}</a>'.format(
                reverse("admin:profiles_familyuser_change", args=(obj.family.id,)),
                obj.family.full_name,
            )
        )


@admin.register(Transport)
class TransportAdmin(SportfacModelAdmin):
    pass


@admin.register(ChildActivityLevel)
class ChildActivityLevelAdmin(SportfacModelAdmin):
    list_display = ("child", "activity")
    list_filter = ("activity",)
    raw_id_fields = ("child",)
    search_fields = (
        "child__first_name",
        "child__last_name",
        "activity__name",
    )


@admin.register(RegistrationValidation)
class RegistrationValidationAdmin(SportfacModelAdmin):
    list_display = ("user", "consent_given", "modified")
    raw_id_fields = ("user",)
    search_fields = (
        "user__first_name",
        "user__last_name",
    )
