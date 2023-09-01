from django.conf import settings
from django.contrib.auth import views as auth_views
from django.urls import path, re_path, reverse_lazy
from django.views.generic.base import RedirectView

from .forms import AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from .views import (
    AccountRedirectView,
    AccountView,
    LogoutView,
    RegistrationView,
    WizardRegistrationView,
)


app_name = "profiles"

urlpatterns = [
    path("", AccountView.as_view(), name="profiles_account"),
    path("new", RegistrationView.as_view(), name="anytime_registeraccount"),
    path("register", WizardRegistrationView.as_view(), name="registeraccount"),
    path("logout", LogoutView.as_view(), name="auth_logout"),
    path("redirect", AccountRedirectView.as_view(), name="authenticated-home"),
]
if settings.KEPCHUP_USE_SSO:
    urlpatterns += [
        path("login", RedirectView.as_view(url=reverse_lazy("profiles:profiles_account"))),
        path(
            "password/change/",
            auth_views.PasswordChangeView.as_view(
                form_class=PasswordChangeForm,
                success_url=reverse_lazy("profiles:password_change_done"),
            ),
            name="password_change",
        ),
        path(
            "password/change/done/",
            auth_views.PasswordChangeDoneView.as_view(),
            name="password_change_done",
        ),
        path(
            "password/reset/",
            auth_views.PasswordResetView.as_view(
                form_class=PasswordResetForm,
                success_url=reverse_lazy("profiles:password_reset_done"),
            ),
            name="password_reset",
        ),
        path(
            "password/reset/done/",
            auth_views.PasswordResetDoneView.as_view(),
            name="password_reset_done",
        ),
        path(
            "password/reset/complete/",
            auth_views.PasswordResetCompleteView.as_view(),
            name="password_reset_complete",
        ),
        re_path(
            "^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
            auth_views.PasswordResetConfirmView.as_view(
                form_class=SetPasswordForm,
                success_url=reverse_lazy("profiles:password_reset_complete"),
            ),
            name="password_reset_confirm",
        ),
        path(
            "reset/",
            auth_views.PasswordResetView.as_view(
                form_class=PasswordResetForm,
                success_url=reverse_lazy("profiles:password_reset_done"),
            ),
            name="registration_reset",
        ),
    ]
else:
    urlpatterns += [
        path(
            "login",
            auth_views.LoginView.as_view(
                template_name="registration/login.html", authentication_form=AuthenticationForm
            ),
            name="auth_login",
        ),
        path(
            "password/change/",
            auth_views.PasswordChangeView.as_view(
                form_class=PasswordChangeForm,
                success_url=reverse_lazy("profiles:password_change_done"),
            ),
            name="password_change",
        ),
        path(
            "password/change/done/",
            auth_views.PasswordChangeDoneView.as_view(),
            name="password_change_done",
        ),
        path(
            "password/reset/",
            auth_views.PasswordResetView.as_view(
                form_class=PasswordResetForm,
                success_url=reverse_lazy("profiles:password_reset_done"),
            ),
            name="password_reset",
        ),
        path(
            "password/reset/done/",
            auth_views.PasswordResetDoneView.as_view(),
            name="password_reset_done",
        ),
        path(
            "password/reset/complete/",
            auth_views.PasswordResetCompleteView.as_view(),
            name="password_reset_complete",
        ),
        re_path(
            r"^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
            auth_views.PasswordResetConfirmView.as_view(
                form_class=SetPasswordForm,
                success_url=reverse_lazy("profiles:password_reset_complete"),
            ),
            name="password_reset_confirm",
        ),
        path(
            "reset/",
            auth_views.PasswordResetView.as_view(
                form_class=PasswordResetForm,
                success_url=reverse_lazy("profiles:password_reset_done"),
            ),
            name="registration_reset",
        ),
    ]
