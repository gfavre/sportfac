from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
import django.contrib.auth.forms as auth_forms
from django.core.urlresolvers import reverse
from django.template.defaultfilters import mark_safe

import floppyforms.__future__ as forms
from localflavor.generic.forms import IBANFormField

from .models import FamilyUser
from backend.forms import Select2Widget, DatePickerInput


__all__ = ('AuthenticationForm', 'PasswordChangeForm', 'PasswordResetForm',
           'AcceptTermsForm', 'RegistrationForm',
           'UserForm', 'ManagerForm', 'ManagerWithPasswordForm',
           'ResponsibleForm', 'ResponsibleWithPasswordForm',
           'UserPayForm')


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
        if not (cleaned_data.get('private_phone', False) or \
                cleaned_data.get('private_phone2', False) or \
                cleaned_data.get('private_phone3', False)):
            raise forms.ValidationError(_("At least one phone number is mandatory"))


class UserForm(PhoneRequiredMixin, forms.ModelForm):
    address = forms.CharField(label=_("Address"),
                              widget=forms.Textarea(attrs={'rows': 3}),
                              required = False)

    email = forms.EmailField(label=_("E-mail"), 
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))
    zipcode = forms.CharField(label=_("NPA"), widget=forms.TextInput(attrs={'placeholder': '1296'}))
    city = forms.CharField(label=_("City"), widget=forms.TextInput(attrs={'placeholder': 'Coppet'}))

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

class ResponsibleForm(ManagerForm):
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
                  'birth_date', 'iban', 'ahv')
    

class ResponsibleWithPasswordForm(ResponsibleForm):
    password1 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password"),
                                required=True)
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password (again)"),
                                required=True)

    def clean(self):
        super(ResponsibleWithPasswordForm, self).clean()
        c = self.cleaned_data
        if self.cleaned_data.get("password1") != self.cleaned_data.get("password2"):
            raise forms.ValidationError(_("You must type the same password"
                                              " each time."))


class UserPayForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('finished_registration', 'paid', )

           
class RegistrationForm(PhoneRequiredMixin, forms.Form):
    """
    Form for registering a new user account.
    
    Validates that the requested username is not already in use, and
    requires the password to be entered twice to catch typos.
    
    Subclasses should feel free to add any additional validation they
    need, but should avoid defining a ``save()`` method -- the actual
    saving of collected user data is delegated to the active
    registration backend.

    """
    required_css_class = 'required'
    email = forms.EmailField(label=_("E-mail"), 
                             max_length=255,
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))
    
    first_name = forms.CharField(label=_("First name"), max_length=30, required=True)
    last_name = forms.CharField(label=_("Last name"),  max_length=30, required=True)
    address = forms.CharField(label=_("Address"),
                              #widget=forms.Textarea(attrs={'rows': 3}),
                              required = False)
    zipcode = forms.CharField(label=_("NPA"), required=True,
                              max_length=5, 
                              widget=forms.TextInput(attrs={'placeholder': _("NPA")}))
    city = forms.CharField(
                label=_("City"),max_length=100,required=True,
                widget=forms.TextInput(attrs={'placeholder': _('City')})
            )
    country = forms.ChoiceField(label=_("Country"), choices=FamilyUser.COUNTRY)

    private_phone = forms.CharField(label=_("Home phone"), max_length=30, widget=forms.PhoneNumberInput(), required=False)
    private_phone2 = forms.CharField(label=_("Mobile phone #1"), max_length=30, widget=forms.PhoneNumberInput(), required=False)
    private_phone3 = forms.CharField(label=_("Mobile phone #2"), max_length=30, widget=forms.PhoneNumberInput(), required=False)

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
            raise forms.ValidationError(_("A user with that username already exists."))
        else:
            return self.cleaned_data['email']
    
    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.
        
        """
        super(RegistrationForm, self).clean()
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))