import django.contrib.auth.views as auth_views
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import FormView, RedirectView, UpdateView

from braces.views import LoginRequiredMixin
from registration import signals
from registrations.models import Bill

from sportfac.views import NotReachableException, WizardMixin

from .forms import InstructorForm, RegistrationForm, UserForm
from .models import FamilyUser


__all__ = (
    "AccountView",
    "WizardAccountView",
    "WizardRegistrationView",
    "AccountRedirectView",
)


class AccountRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_manager or user.is_superuser or user.is_staff:
            return reverse("backend:home")
        if user.is_kepchup_staff:
            return reverse("activities:my-courses")
        return reverse("registrations:registrations_registered_activities")


class _BaseAccount(LoginRequiredMixin, UpdateView):
    model = FamilyUser
    form_class = InstructorForm

    def get_form_class(self):
        user: FamilyUser = self.request.user  # type: ignore
        if user.is_instructor:
            return InstructorForm
        return UserForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user: FamilyUser = self.request.user  # type: ignore
        if user.is_instructor:
            kwargs["user"] = user
        return kwargs

    def get_object(self, queryset=None):
        return self.request.user


class AccountView(SuccessMessageMixin, _BaseAccount):
    template_name = "profiles/account.html"

    def get_success_message(self, form):
        return _("Your contact informations have been saved.")


class WizardAccountView(WizardMixin, _BaseAccount):
    template_name = "profiles/wizard_account.html"
    success_url = reverse_lazy("wizard_children")

    @staticmethod
    def check_initial_condition(request):
        # Condition is to be logged in => _BaseAccount requires login.
        if (
            request.user.is_authenticated
            and Bill.objects.filter(
                family=request.user,
                status=Bill.STATUS.waiting,
                total__gt=0,
                payment_method__in=(Bill.METHODS.datatrans, Bill.METHODS.postfinance),
            ).exists()
        ):
            raise NotReachableException("Payment expected first")


class RegistrationBaseView(FormView):
    form_class = RegistrationForm

    def form_valid(self, form):
        self.register(form)
        success_url = self.get_success_url()

        # success_url may be a simple string, or a tuple providing the
        # full argument set for redirect(). Attempting to unpack it
        # tells us which one it is.
        try:
            to, args, kwargs = success_url
        except ValueError:
            return redirect(success_url)
        else:
            return redirect(to, *args, **kwargs)

    def register(self, form):
        email, password = form.cleaned_data["email"], form.cleaned_data["password1"]
        first_name, last_name = form.cleaned_data["first_name"], form.cleaned_data["last_name"]
        address, zipcode, city = (
            form.cleaned_data["address"],
            form.cleaned_data["zipcode"],
            form.cleaned_data["city"],
        )
        country = form.cleaned_data["country"]
        private_phone = form.cleaned_data["private_phone"]
        private_phone2 = form.cleaned_data["private_phone2"]
        private_phone3 = form.cleaned_data["private_phone3"]

        FamilyUser.objects.create_user(
            first_name=first_name,
            last_name=last_name,
            password=password,
            email=email,
            address=address,
            zipcode=zipcode,
            city=city,
            country=country,
            private_phone=private_phone,
            private_phone2=private_phone2,
            private_phone3=private_phone3,
        )
        user = authenticate(email=email, password=password)
        login(self.request, user)
        signals.user_registered.send(sender=self.__class__, user=user, request=self.request)
        return user


class RegistrationView(RegistrationBaseView):
    template_name = "profiles/registration_form.html"

    def get_success_url(self):
        return reverse("profiles:profiles_account")

    def dispatch(self, request, *args, **kwargs):
        """Called before get or post methods"""
        if settings.KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME or request.REGISTRATION_OPENED:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


class WizardRegistrationView(WizardMixin, RegistrationBaseView):
    """
    A registration backend which implements the simplest possible
    workflow: a user supplies a username, email address and password
    (the bare minimum for a useful account), and is immediately signed
    up and logged in).
    """

    form_class = RegistrationForm
    template_name = "profiles/wizard_registration_form.html"

    @staticmethod
    def check_initial_condition(request):
        return

    def get_success_url(self):
        return reverse("wizard_children")


class LogoutView(auth_views.LogoutView):
    def get_next_page(self):
        if settings.KEPCHUP_USE_SSO:
            # FIXME: wgat is this hardcoded crap?
            return "https://users.ssfmontreux.ch/logout"
        return super().get_next_page()
