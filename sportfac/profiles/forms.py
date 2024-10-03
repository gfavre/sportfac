import django.contrib.auth.forms as auth_forms
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils.translation import gettext_lazy as _

from activities.models import Activity
from backend.forms import ActivityMultipleWidget
from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Fieldset, Layout, Submit

# noinspection PyPackageRequirements
from localflavor.generic.forms import IBANFormField
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import RegionalPhoneNumberWidget

from .models import FamilyUser


__all__ = (
    "AuthenticationForm",
    "PasswordChangeForm",
    "PasswordResetForm",
    "SetPasswordForm",
    "AcceptTermsForm",
    "RegistrationForm",
    "UserForm",
    "ManagerForm",
    "InstructorForm",
)


class AuthenticationForm(auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-3"
        self.helper.field_class = "col-sm-9"
        reset_url = reverse("profiles:password_reset")
        reset_text = _("Forgotten your password or username?")
        self.fields["password"].help_text = mark_safe(f'<a href="{reset_url}">{reset_text}</a>')


class PasswordChangeForm(auth_forms.PasswordChangeForm):
    old_password = forms.CharField(label=_("Old password"), widget=forms.PasswordInput)
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-3"
        self.helper.field_class = "col-sm-9"


class PasswordResetForm(auth_forms.PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={"placeholder": "john@example.com"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            "email",
            Submit("submit", _("Reset my password"), css_class="btn-primary"),
        )


class SetPasswordForm(auth_forms.SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class AcceptTermsForm(forms.Form):
    accept = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={"style": "margin-top:0;"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["accept"].label = mark_safe(
            _("""I've read and agree to the full <a href="%s">terms and conditions</a>""") % reverse("terms")
        )


class PhoneRequiredMixin:
    def clean(self):
        # noinspection PyUnresolvedReferences
        cleaned_data = super().clean()
        if not (
            cleaned_data.get("private_phone", False)
            or cleaned_data.get("private_phone2", False)
            or cleaned_data.get("private_phone3", False)
        ):
            raise forms.ValidationError(_("At least one phone number is mandatory"))


class UserForm(PhoneRequiredMixin, forms.ModelForm):
    address = forms.CharField(label=_("Address"), widget=forms.Textarea(attrs={"rows": 3}), required=True)
    email = forms.EmailField(label=_("E-mail"), widget=forms.EmailInput(attrs={"placeholder": "john@example.com"}))
    city = forms.CharField(label=_("City"), widget=forms.TextInput(attrs={"placeholder": _("City")}))
    private_phone = PhoneNumberField(
        label=_("Home phone"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )
    private_phone2 = PhoneNumberField(
        label=_("Mobile phone #1"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )
    private_phone3 = PhoneNumberField(
        label=_("Mobile phone #2"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )
    password1 = forms.CharField(widget=forms.PasswordInput, label=_("Password"), required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("Password (again)"), required=False)

    class Meta:
        model = get_user_model()
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
            "private_phone3",
        )

    def clean(self):
        super().clean()
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError(_("You must type the same password each time."))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["zipcode"].required = True

        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.form_tag = False
        self.helper.include_media = False

        self.helper.layout = Layout()
        if self.initial:
            password_change = reverse("backend:password-change", args=[self.instance.pk])
            password_label = _("Change password")
            self.helper.layout.append(
                Fieldset(
                    _("Login informations"),
                    "email",
                    HTML(f"""<p><a href="{password_change}">{password_label}</a></p>"""),
                ),
            )
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True
            self.helper.layout.append(
                Fieldset(
                    _("Login informations"),
                    "email",
                    "password1",
                    "password2",
                )
            )

        if settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES:
            self.fields["private_phone"].required = True
            self.fields["private_phone"].label = _("Mobile phone")

        self.helper.layout.append(
            Fieldset(
                _("Contact informations"),
                "first_name",
                "last_name",
                "address",
                "zipcode",
                "city",
                not settings.KEPCHUP_REGISTRATION_HIDE_COUNTRY and "country" or HTML(""),
                "private_phone",
                not settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES and "private_phone2" or HTML(""),
                not settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES and "private_phone3" or HTML(""),
            )
        )


class InstructorForm(UserForm):
    iban = IBANFormField(label=_("IBAN"), widget=forms.TextInput(attrs={"placeholder": "CH37..."}), required=False)
    birth_date = forms.DateTimeField(
        label=_("Birth date"),
        widget=DatePickerInput(format="%d.%m.%Y"),
        help_text=_("Format: 31.12.2012"),
        required=False,
    )

    class Meta:
        model = get_user_model()
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
            "private_phone3",
            "birth_date",
            "iban",
            "bank_name",
            "ahv",
            "js_identifier",
            "is_mep",
            "is_teacher",
            "external_identifier",
            "gender",
            "nationality",
            "permit_type",
        )
        widgets = {
            "ahv": forms.TextInput(attrs={"placeholder": "756.1234.5678.95"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.helper.layout.append(
            Fieldset(
                _("Instructor informations"),
                settings.KEPCHUP_INSTRUCTORS_DISPLAY_EXTERNAL_ID and "external_identifier" or HTML(""),
                "ahv",
                "gender",
                "birth_date",
                "nationality",
                "permit_type",
                "iban",
                "bank_name",
                "js_identifier",
                "is_mep",
                "is_teacher",
            )
        )


class ManagerForm(InstructorForm):
    managed_activities = forms.ModelMultipleChoiceField(
        label=_("Rights on activities"),
        queryset=Activity.objects.all(),
        widget=ActivityMultipleWidget(),
        required=False,
    )

    is_manager = forms.BooleanField(
        required=False,
        label=_("Is a manager"),
        help_text=_("Grant access for this user to this backend interface"),
    )
    is_restricted_manager = forms.BooleanField(
        label=_("Restricted manager"),
        required=False,
        help_text=_("Grant access for this user on specific activities"),
    )

    def clean(self):
        super().clean()
        is_restricted_manager = self.cleaned_data.get("is_restricted_manager")
        managed_activities = self.cleaned_data.get("managed_activities")

        # If is_restricted_manager is not ticked, ensure managed_activities is empty
        if not is_restricted_manager and managed_activities:
            self.add_error("managed_activities", _("Managed activities must be empty if not a restricted manager."))

        return self.cleaned_data

    def save(self, commit=True):
        self.instance.is_restricted_manager = self.cleaned_data.get("is_restricted_manager", False)
        self.instance.is_manager = self.cleaned_data.get("is_manager", False)
        instance = super().save(commit=False)
        if commit:
            instance.save()
            if "managed_activities" in self.cleaned_data:
                instance.managed_activities.clear()
                for activity in self.cleaned_data["managed_activities"]:
                    instance.managed_activities.add(activity)
        return instance

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.user.is_full_manager:
            return
        instance = kwargs["instance"]
        if instance:
            self.fields["is_manager"].initial = instance.is_manager
            self.fields["is_restricted_manager"].initial = instance.is_restricted_manager
            self.fields["managed_activities"].initial = instance.managed_activities.all()
        self.helper.layout.append(
            Fieldset(
                _("Management access"),
                "is_manager",
                HTML("<hr>"),
                "is_restricted_manager",
                "managed_activities",
            )
        )


class RegistrationForm(PhoneRequiredMixin, forms.Form):
    """
    Form for registering a new user account.

    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.

    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend."""

    required_css_class = "required"
    email = forms.EmailField(
        label=_("E-mail"),
        max_length=255,
        widget=forms.EmailInput(attrs={"placeholder": "john@example.com"}),
    )
    email2 = forms.EmailField(
        label=_("Email (again)"),
        max_length=255,
        widget=forms.EmailInput(),
        help_text=_("Enter the same email as before, for verification."),
    )
    first_name = forms.CharField(label=_("First name"), max_length=30, required=True)
    last_name = forms.CharField(label=_("Last name"), max_length=30, required=True)
    address = forms.CharField(label=_("Address"), widget=forms.Textarea(attrs={"rows": 3}), required=True)
    zipcode = forms.CharField(
        label=_("NPA"),
        required=True,
        max_length=5,
        widget=forms.TextInput(attrs={"placeholder": _("NPA")}),
    )
    city = forms.CharField(
        label=_("City"),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("City")}),
    )
    country = forms.ChoiceField(label=_("Country"), choices=FamilyUser.COUNTRY)

    private_phone = PhoneNumberField(
        label=_("Home phone"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )
    private_phone2 = PhoneNumberField(
        label=_("Mobile phone #1"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )
    private_phone3 = PhoneNumberField(
        label=_("Mobile phone #2"),
        max_length=30,
        widget=RegionalPhoneNumberWidget(attrs={"class": "form-control"}),
        required=False,
    )

    password1 = forms.CharField(widget=forms.PasswordInput, label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_("Password (again)"))

    def clean_email(self):
        """
        Validate that the email is alphanumeric and is not already
        in use.
        """
        existing = get_user_model().objects.filter(email__iexact=self.cleaned_data["email"])
        if existing.exists():
            message = _("A user with that username already exists.")
            message += (
                ' <a href="%s" class="btn-link" style="margin-right:1em"><i class="icon-lock-open"></i>%s</a>'
                % (reverse("profiles:auth_login"), _("Login"))
            )
            message += ' <a href="#" class="new-mail btn-link"><i class="icon-cancel-circled"></i>%s</a>' % _(
                "Use another email address"
            )
            raise forms.ValidationError(mark_safe(message))
        return self.cleaned_data["email"]

    def clean_email2(self):
        email1 = self.cleaned_data.get("email")
        email2 = self.cleaned_data.get("email2")
        if email1 and email2 and email1 != email2:
            raise forms.ValidationError(_("The two email fields didn't match."))
        return email2

    def clean(self):
        """
        Verify that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        """
        super().clean()
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError(_("The two password fields didn't match."))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.layout = Layout(
            Fieldset(
                _("Contact informations"),
                "first_name",
                "last_name",
                "address",
                "zipcode",
                "city",
                not settings.KEPCHUP_REGISTRATION_HIDE_COUNTRY and "country",
                settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES
                and Field("private_phone", label=_("Mobile phone"))
                or Field("private_phone"),
                not settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES and "private_phone2",
                not settings.KEPCHUP_REGISTRATION_HIDE_OTHER_PHONES and "private_phone3",
            ),
            Fieldset(
                _("Login informations"),
                "email",
                "email2",
                "password1",
                "password2",
            ),
        )
