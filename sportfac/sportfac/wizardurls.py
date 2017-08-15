from django.conf.urls import url

from activities.views import ActivityListView
from profiles.views import WizardAccountView, WizardRegistrationView
from registrations.views import (RegisteredActivitiesListView, WizardChildrenListView, 
                                 WizardBillingView)
from .views import WizardView

urlpatterns = [
    url(r'^$', WizardView.as_view(), name='wizard'),
    url(r'^register/$', WizardRegistrationView.as_view(), name='wizard_register'),  # no account yet
    url(r'^account/$', WizardAccountView.as_view(), name='wizard_account'),  # account created
    url(r'^children/$', WizardChildrenListView.as_view(), name="wizard_children"),
    url(r'^activities/$', ActivityListView.as_view(), name='wizard_activities'),
    url(r'^confirm/$', RegisteredActivitiesListView.as_view(), name="wizard_confirm"),
    url(r'^billing/$', WizardBillingView.as_view(), name="wizard_billing"),
]
