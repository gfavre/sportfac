from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import url
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic.base import RedirectView

from .forms import AuthenticationForm
from .views import (AccountRedirectView, AccountView, LogoutView, RegistrationView,
                    WizardRegistrationView, password_change, password_reset)


app_name = "profiles"

urlpatterns = [
    url(r"^$", AccountView.as_view(), name="profiles_account"),
    url(r"^new/$", RegistrationView.as_view(), name="anytime_registeraccount"),
    url(r"^register/$", WizardRegistrationView.as_view(), name="registeraccount"),
    url(r"^logout/$", LogoutView.as_view(), name="auth_logout"),
    url(r"^redirect/$", AccountRedirectView.as_view(), name="authenticated-home"),
]
if settings.KEPCHUP_USE_SSO:
    urlpatterns += [
        url(r"^login/$", RedirectView.as_view(url=reverse_lazy("profiles_account"))),
        url(r"^password/change/$", password_change, name="password_change"),
        url(
            r"^password/change/done/$",
            auth_views.PasswordChangeDoneView.as_view(),
            name="password_change_done",
        ),
        url(r"^password/reset/$", password_reset, name="password_reset"),
        url(
            r"^password/reset/done/$",
            auth_views.PasswordResetDoneView.as_view(),
            name="password_reset_done",
        ),
        url(
            r"^password/reset/complete/$",
            auth_views.PasswordResetCompleteView.as_view(),
            name="password_reset_complete",
        ),
        url(
            r"^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
            auth_views.PasswordResetConfirmView.as_view(),
            name="password_reset_confirm",
        ),
        url(r"^reset/$", password_reset, name="registration_reset"),
    ]
else:
    urlpatterns += [
        url(
            r"^login/$",
            auth_views.LoginView.as_view(
                template_name="registration/login.html", authentication_form=AuthenticationForm
            ),
            name="auth_login",
        ),
        url(r"^password/change/$", password_change, name="password_change"),
        url(
            r"^password/change/done/$",
            auth_views.PasswordChangeDoneView.as_view(),
            name="password_change_done",
        ),
        url(r"^password/reset/$", password_reset, name="password_reset"),
        url(
            r"^password/reset/done/$",
            auth_views.PasswordResetDoneView.as_view(),
            name="password_reset_done",
        ),
        url(
            r"^password/reset/complete/$",
            auth_views.PasswordResetCompleteView.as_view(),
            name="password_reset_complete",
        ),
        url(
            r"^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$",
            auth_views.PasswordResetConfirmView.as_view(),
            name="password_reset_confirm",
        ),
        url(r"^reset/$", password_reset, name="registration_reset"),
    ]
