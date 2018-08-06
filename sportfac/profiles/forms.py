from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
import django.contrib.auth.forms as auth_forms
from django.core.urlresolvers import reverse
from django.template.defaultfilters import mark_safe

import floppyforms.__future__ as forms
from localflavor.generic.forms import IBANFormField
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberInternationalFallbackWidget


from .models import FamilyUser
from backend.forms import DatePickerInput


__all__ = ('AuthenticationForm', 'PasswordChangeForm', 'PasswordResetForm',
           'AcceptTermsForm', 'RegistrationForm',
           'UserForm', 'ManagerForm', 'ManagerWithPasswordForm',
           'InstructorForm', 'InstructorWithPasswordForm')


class AuthenticationForm(auth_forms.AuthenticationForm):
    def __init__(self, *args, **kwargs):
        "Convert to floppyform"
        super(AuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget = forms.TextInput()
        self.fields['password'].widget = forms.PasswordInput()


class PasswordChangeForm(auth_forms.PasswordChangeForm):
    old_password = forms.CharField(label=_("Old password"),
                                   widget=forms.PasswordInput)
    new_password1 = forms.CharField(label=_("New password"),
                                    widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"),
                                    widget=forms.PasswordInput)


class PasswordResetForm(auth_forms.PasswordResetForm):
    email = forms.EmailField(label=_("Email"), max_length=254,
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))


class AcceptTermsForm(forms.Form):
    accept = forms.BooleanField(required=True, widget=forms.CheckboxInput(attrs={'style': 'margin-top:0;'}))

    def __init__(self, *args, **kwargs):
        super(AcceptTermsForm, self).__init__(*args, **kwargs)
        self.fields['accept'].label = mark_safe(
            _("""I've read and agree to <a href="%s"> terms and conditions</a>""") % reverse('terms')
        )


class PhoneRequiredMixin(object):
    def clean(self):
        cleaned_data = super(PhoneRequiredMixin, self).clean()
        if not (cleaned_data.get('private_phone', False) or
                cleaned_data.get('private_phone2', False) or
                cleaned_data.get('private_phone3', False)):
            raise forms.ValidationError(_("At least one phone number is mandatory"))


class UserForm(PhoneRequiredMixin, forms.ModelForm):
    address = forms.CharField(label=_("Address"),
                              widget=forms.Textarea(attrs={'rows': 3}),
                              required=True)
    email = forms.EmailField(label=_("E-mail"),
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))
    zipcode = forms.CharField(label=_("NPA"), widget=forms.TextInput(attrs={'placeholder': _("NPA")}))
    city = forms.CharField(label=_("City"), widget=forms.TextInput(attrs={'placeholder': _("City")}))
    private_phone = PhoneNumberField(label=_("Home phone"), max_length=30,
                                     widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                     required=False)
    private_phone2 = PhoneNumberField(label=_("Mobile phone #1"), max_length=30,
                                      widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                      required=False)
    private_phone3 = PhoneNumberField(label=_("Mobile phone #2"), max_length=30,
                                      widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                      required=False)

    class Meta:
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', 'address',
                  'zipcode', 'city', 'country',
                  'private_phone', 'private_phone2', 'private_phone3')


class ManagerForm(UserForm):
    is_manager = forms.BooleanField(required=False, label=_("Is a manager"),
                                    help_text=_("Grant access for this user to this backend interface"))

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        instance = kwargs['instance']
        if instance:
            self.fields['is_manager'].initial = instance.is_manager


class ManagerWithPasswordForm(ManagerForm):
    password1 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password"),
                                required=True)
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password (again)"),
                                required=True)

    def clean(self):
        super(ManagerWithPasswordForm, self).clean()
        c = self.cleaned_data
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError(_("You must type the same password"
                                              " each time."))


class InstructorForm(ManagerForm):
    iban = IBANFormField(label=_("IBAN"),
                         widget=forms.TextInput(attrs={'placeholder': 'CH37...'}),
                         required=False)
    birth_date = forms.DateTimeField(label=_("Birth date"),
                                     widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("Format: 31.12.2012"), required=False)

    class Meta:
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', 'address',
                  'zipcode', 'city', 'country',
                  'private_phone', 'private_phone2', 'private_phone3',
                  'birth_date', 'iban', 'ahv', 'js_identifier')


class InstructorWithPasswordForm(InstructorForm):
    password1 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password"),
                                required=True)
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password (again)"),
                                required=True)

    def clean(self):
        super(InstructorWithPasswordForm, self).clean()
        c = self.cleaned_data
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError(_("You must type the same password each time."))


class RegistrationForm(PhoneRequiredMixin, forms.Form):
    """
    Form for registering a new user account.

    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.

    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend."""
    required_css_class = 'required'
    email = forms.EmailField(label=_("E-mail"),
                             max_length=255,
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))
    email2 = forms.EmailField(label=_("Email (again)"),
                              max_length=255,
                              widget=forms.EmailInput(),
                              help_text=_("Enter the same email as before, for verification."))
    first_name = forms.CharField(label=_("First name"), max_length=30, required=True)
    last_name = forms.CharField(label=_("Last name"), max_length=30, required=True)
    address = forms.CharField(label=_("Address"),
                              widget=forms.Textarea(attrs={'rows': 3}),
                              required=True)
    zipcode = forms.CharField(label=_("NPA"), required=True,
                              max_length=5,
                              widget=forms.TextInput(attrs={'placeholder': _("NPA")}))
    city = forms.CharField(
                label=_("City"), max_length=100, required=True,
                widget=forms.TextInput(attrs={'placeholder': _('City')})
            )
    country = forms.ChoiceField(label=_("Country"), choices=FamilyUser.COUNTRY)

    private_phone = PhoneNumberField(label=_("Home phone"), max_length=30,
                                     widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                     required=False)
    private_phone2 = PhoneNumberField(label=_("Mobile phone #1"), max_length=30,
                                      widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                      required=False)
    private_phone3 = PhoneNumberField(label=_("Mobile phone #2"), max_length=30,
                                      widget=PhoneNumberInternationalFallbackWidget(attrs={'class': 'form-control'}),
                                      required=False)

    password1 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password (again)"))

    def clean_email(self):
        """
        Validate that the email is alphanumeric and is not already
        in use.
        """
        existing = get_user_model().objects.filter(email__iexact=self.cleaned_data['email'])
        if existing.exists():
            message = _("A user with that username already exists.")
            message += ' <a href="%s" class="btn-link" style="margin-right:1em"><i class="icon-lock-open"></i>%s</a>' % (reverse('auth_login'), _("Login"))
            message += ' <a href="#" class="new-mail btn-link"><i class="icon-cancel-circled"></i>%s</a>' % _("Use another email address")
            raise forms.ValidationError(mark_safe(message))
        else:
            return self.cleaned_data['email']

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
        super(RegistrationForm, self).clean()
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
