from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.forms import Form

import floppyforms as forms


class RegistrationForm(Form):
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
                             widget=forms.EmailInput(attrs={'placeholder': 'john@example.com'}))
    password1 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password"))
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label=_("Password (again)"))
                                
    first_name = forms.CharField(label=_("First name"))
    last_name = forms.CharField(label=_("Last name"))
    address = forms.CharField(label=_("Address"),
                              widget=forms.Textarea(attrs={'rows': 3}),
                              required = False)
    zipcode = forms.IntegerField(label=_("NPA"), min_value=1000, max_value=9999)
    city = forms.CharField(label=_("City"), widget=forms.TextInput(attrs={'placeholder': 'Coppet'}))
    private_phone = forms.CharField(label=_("Private phone"), widget=forms.PhoneNumberInput(), required=True)
    private_phone2 = forms.CharField(label=_("Other private phone"), widget=forms.PhoneNumberInput(), required=False)
    
        
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
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data
