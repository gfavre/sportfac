import django.contrib.auth.views as auth_views
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.generic import FormView, RedirectView, UpdateView

from braces.views import LoginRequiredMixin
from registration import signals

from wizard.views import BaseWizardStepView
from .forms import InstructorForm, RegistrationForm, UserForm
from .models import FamilyUser


__all__ = (
    "AccountView",
    "WizardFamilyUserCreateView",
    "WizardFamilyUserUpdateView",
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


class RegistrationView(RegistrationBaseView):  # deprecated
    template_name = "profiles/registration_form.html"

    def get_success_url(self):
        return reverse("profiles:profiles_account")

    def dispatch(self, request, *args, **kwargs):
        """Called before get or post methods"""
        if settings.KEPCHUP_REGISTER_ACCOUNTS_AT_ANY_TIME or request.REGISTRATION_OPENED:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


class WizardFamilyUserCreateView(BaseWizardStepView, RegistrationBaseView):
    form_class = RegistrationForm
    template_name = "wizard/account-create.html"
    step_slug = "user-create"

    def get_context_data(self, **kwargs):
        """Merge the UpdateView context with the BaseWizardStepView context."""
        context = super().get_context_data(**kwargs)
        context["LOGIN_URL"] = settings.LOGIN_URL if settings.KEPCHUP_USE_SSO else reverse(settings.LOGIN_URL)
        form_context = RegistrationBaseView.get_context_data(self, **kwargs)
        context.update(form_context)
        return context

    def get_success_url(self):
        """Determine the next step based on the workflow."""
        return reverse("wizard:step", kwargs={"step_slug": "children"})

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        user: FamilyUser = request.user  # noqa
        if user.is_authenticated:
            return redirect(reverse("wizard:step", kwargs={"step_slug": "user-update"}))
        return super().get(request, *args, **kwargs)


class WizardFamilyUserUpdateView(LoginRequiredMixin, BaseWizardStepView, UpdateView):
    model = FamilyUser
    template_name = "wizard/account.html"
    step_name = "update_family_user"
    step_slug = "user-update"

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

    def get_context_data(self, **kwargs):
        """Merge the UpdateView context with the BaseWizardStepView context."""
        context = super().get_context_data(**kwargs)
        form_context = UpdateView.get_context_data(self, **kwargs)
        context.update(form_context)
        return context


class LogoutView(auth_views.LogoutView):
    def get_next_page(self):
        if settings.KEPCHUP_USE_SSO:
            # FIXME: wgat is this hardcoded crap?
            return "https://users.ssfmontreux.ch/logout"
        return super().get_next_page()
