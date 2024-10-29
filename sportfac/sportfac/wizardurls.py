from django.urls import path

from activities.views import ActivityListView
from appointments.views.register import WizardSlotsView
from payments.views import PaymentFailureView, PaymentSuccessView
from profiles.views import WizardAccountView, WizardRegistrationView
from registrations.views.user import (
    RegisteredActivitiesListView,
    WizardBillingView,
    WizardCancelRegistrationView,
    WizardChildrenListView,
)
from .views import WizardView


urlpatterns = [
    path("", WizardView.as_view(), name="wizard"),
    path("register/", WizardRegistrationView.as_view(), name="wizard_register"),  # no account yet
    path("account/", WizardAccountView.as_view(), name="wizard_account"),  # account created
    path("children/", WizardChildrenListView.as_view(), name="wizard_children"),
    path("activities/", ActivityListView.as_view(), name="wizard_activities"),
    path("confirm/", RegisteredActivitiesListView.as_view(), name="wizard_confirm"),
    path("appointments/", WizardSlotsView.as_view(), name="wizard_appointments"),
    path("billing/", WizardBillingView.as_view(), name="wizard_billing"),
    path("cancel/", WizardCancelRegistrationView.as_view(), name="wizard_cancel"),
    path("payment/failure/", PaymentFailureView.as_view(), name="wizard_payment_failure"),
    path("payment/success/", PaymentSuccessView.as_view(), name="wizard_payment_success"),
]
