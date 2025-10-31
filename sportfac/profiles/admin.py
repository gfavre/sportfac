from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _

from registrations.models import Child
from registrations.tasks import send_confirmation
from sportfac.admin_utils import SportfacAdminMixin
from sportfac.admin_utils import SportfacModelAdmin

from .models import City
from .models import FamilyUser
from .models import School
from .models import SchoolYear


@admin.action(description="Envoyer confirmation (Celery)")
def send_confirmation_action(modeladmin, request, queryset):
    from backend.models import Domain

    domain = Domain.objects.filter(is_current=True).first()
    tenant = domain.tenant if domain else None
    for user in queryset:
        send_confirmation.delay(user.pk, tenant.pk)


class FamilyCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = FamilyUser
        fields = (
            "email",
            "first_name",
            "last_name",
            "address",
            "zipcode",
            "city",
            "country",
            "private_phone",
            "private_phone2",
            "birth_date",
            "iban",
            "ahv",
            "js_identifier",
            "is_mep",
            "is_teacher",
            "gender",
            "nationality",
            "permit_type",
            "bank_name",
            "external_identifier",
        )

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class FamilyChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    password = ReadOnlyPasswordHashField(
        help_text=_(
            "Raw passwords are not stored, so there is no way to see "
            "this user's password, but you can change the password "
            'using <a href="../password/">this form</a>.'
        )
    )

    class Meta:
        model = FamilyUser
        fields = (
            "email",
            "is_staff",
            "is_superuser",
            "groups",
            "first_name",
            "last_name",
            "address",
            "zipcode",
            "city",
            "country",
            "private_phone",
            "private_phone2",
            "private_phone3",
            "birth_date",
            "iban",
            "ahv",
            "js_identifier",
            "is_mep",
            "is_teacher",
            "gender",
            "nationality",
            "permit_type",
            "bank_name",
            "external_identifier",
        )

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


class ChildInline(admin.StackedInline):
    model = Child
    extra = 1
    verbose_name = _("child")
    verbose_name_plural = _("children")


@admin.register(FamilyUser)
class FamilyAdmin(SportfacAdminMixin, UserAdmin):
    # The forms to add and change user instances
    form = FamilyChangeForm
    add_form = FamilyCreationForm

    list_display = (
        "email",
        "first_name",
        "last_name",
        "children_names",
        "last_login",
        "date_joined",
        "course_names",
        "is_instructor",
    )
    # change_list_filter_template = "admin/filter_listing.html"
    list_filter = ("is_staff", "is_superuser", "is_active", "is_manager", "is_restricted_manager")
    # filter_horizontal = ("managed_activities",)

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "is_manager",
                    "is_restricted_manager",
                    # "managed_activities",
                )
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "address",
                    "zipcode",
                    "city",
                    "country",
                    "private_phone",
                    "private_phone2",
                    "private_phone3",
                )
            },
        ),
        (
            _("Instructor infos"),
            {
                "fields": [
                    "external_identifier",
                    "birth_date",
                    "gender",
                    "ahv",
                    ("nationality", "permit_type"),
                    ("is_mep", "is_teacher"),
                    ("iban", "bank_name"),
                ]
            },
        ),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
        (
            "Personal info",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "address",
                    "zipcode",
                    "city",
                    "country",
                    "private_phone",
                    "private_phone2",
                    "birth_date",
                    "iban",
                    "ahv",
                )
            },
        ),
    )
    search_fields = (
        "email",
        "last_name",
        "first_name",
    )
    ordering = ("last_name", "first_name")
    actions = [
        send_confirmation_action,
    ]
    # inlines = [ChildInline]


@admin.register(City)
class CityAdmin(SportfacModelAdmin):
    list_display = ("zipcode", "name", "country")
    search_fields = ("zipcode", "name")
    list_filter = ("country",)


@admin.register(SchoolYear)
class SchoolYearAdmin(SportfacModelAdmin):
    list_display = ("year", "visible")
    list_filter = ("visible",)


@admin.register(School)
class SchoolAdmin(SportfacModelAdmin):
    list_display = ("name", "selectable")
    list_filter = ("selectable",)
