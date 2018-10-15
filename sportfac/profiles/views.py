from django.contrib.auth import authenticate, login
import django.contrib.auth.views as auth_views
from django.conf import settings
from django.core.urlresolvers import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.views.generic import UpdateView, FormView

from braces.views import LoginRequiredMixin
#from registration.backends.simple.views import RegistrationView as BaseRegistrationView
#from registration import signals

from sportfac.views import WizardMixin
from .models import FamilyUser
from .forms import RegistrationForm, InstructorForm, PasswordChangeForm, PasswordResetForm


__all__ = ('password_change', 'password_reset',
           'AccountView', 'RegistrationView',
           'WizardAccountView', 'WizardRegistrationView')


def password_change(request):
    """Wrap the built-in password reset view and pass it the arguments"""
    return auth_views.password_change(request, password_change_form=PasswordChangeForm)


def password_reset(request):
    """Wrap the built-in password reset view and pass it the arguments"""
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


class WizardRegistrationView(WizardMixin, FormView):
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

    def form_valid(self, form):
        new_user = self.register(form)
        success_url = self.get_success_url(new_user)

        # success_url may be a simple string, or a tuple providing the
        # full argument set for redirect(). Attempting to unpack it
        # tells us which one it is.
        try:
            to, args, kwargs = success_url
        except ValueError:
            return redirect(success_url)
        else:
            return redirect(to, *args, **kwargs)

    def registration_allowed(self):
        """
        Indicate whether account registration is currently permitted,
        based on the value of the setting ``REGISTRATION_OPEN``. This
        is determined as follows:
        * If ``REGISTRATION_OPEN`` is not specified in settings, or is
          set to ``True``, registration is permitted.
        * If ``REGISTRATION_OPEN`` is both specified and set to
          ``False``, registration is not permitted.
        """
        return getattr(settings, 'REGISTRATION_OPEN', True)

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
