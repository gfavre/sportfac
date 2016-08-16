from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import password_change as auth_password_change
import django.contrib.auth.views as auth_views
from django.contrib.messages.views import SuccessMessageMixin
from django.utils.translation import ugettext as _
from django.views.generic import ListView, UpdateView, TemplateView, FormView

from braces.views import LoginRequiredMixin
from registration.backends.simple.views import RegistrationView as BaseRegistrationView
from registration import signals

from .models import FamilyUser
from .forms import RegistrationForm, InstructorForm, PasswordChangeForm, PasswordResetForm
from registrations.models import Child, Registration
from sportfac.views import WizardMixin


__all__ = ('password_change', 'password_reset', 
           'AccountView', 'RegistrationView', 
           'WizardAccountView', 'WizardRegistrationView')



def password_change(request):
    "Wrap the built-in password reset view and pass it the arguments"
    return auth_views.password_change(request, password_change_form=PasswordChangeForm)


def password_reset(request):
    "Wrap the built-in password reset view and pass it the arguments"
    return auth_views.password_reset(request, password_reset_form=PasswordResetForm)


class _BaseAccount(LoginRequiredMixin, UpdateView):
    model = FamilyUser
    form_class = InstructorForm
    
    def get_object(self, queryset=None):
        return self.request.user


class AccountView(SuccessMessageMixin, _BaseAccount):
    template_name = 'profiles/account.html'
    
    def get_success_message(self, form):
        return _('Your contact informations have been saved.')
    

class WizardAccountView(WizardMixin, _BaseAccount):
    template_name = 'profiles/wizard_account.html'
    success_url = reverse_lazy('wizard_children')


class WizardRegistrationView(WizardMixin, BaseRegistrationView):
    """
    A registration backend which implements the simplest possible
    workflow: a user supplies a username, email address and password
    (the bare minimum for a useful account), and is immediately signed
    up and logged in).
    """
    form_class = RegistrationForm
    template_name = 'profiles/registration_form.html'

    def get_success_url(self, user):
        return reverse('wizard_children')    
       
    def register(self, form):
        email, password = form.cleaned_data['email'], form.cleaned_data['password1']
        first_name, last_name = form.cleaned_data['first_name'], form.cleaned_data['last_name']
        address, zipcode, city = form.cleaned_data['address'], form.cleaned_data['zipcode'], form.cleaned_data['city']
        country = form.cleaned_data['country']
        private_phone = form.cleaned_data['private_phone']
        private_phone2 = form.cleaned_data['private_phone2']
        private_phone3 = form.cleaned_data['private_phone3']
        
        user = FamilyUser.objects.create_user(
            first_name=first_name, last_name=last_name, 
            password=password, email=email,
            address=address, zipcode=zipcode, city=city, country=country,
            private_phone=private_phone,
            private_phone2=private_phone2,
            private_phone3=private_phone3
        )
        user = authenticate(email=email, password=password)
        login(self.request, user)
        signals.user_registered.send(
            sender=self.__class__,
            user=user,
            request=self.request
        )
        return user