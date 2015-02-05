from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

from activities.views import ActivityListView
from profiles.views import (WizardAccountView, WizardRegistrationView,
                            WizardChildrenListView, 
                            RegisteredActivitiesListView, WizardBillingView,)
from .views import WizardView

urlpatterns = patterns('',
    url(r'^$', WizardView.as_view(), name='wizard' ),
    url(r'^register/$', WizardRegistrationView.as_view(), name='wizard_register'), # no account yet
    url(r'^account/$', WizardAccountView.as_view(), name='wizard_account'), # account created
    url(r'^children/$', WizardChildrenListView.as_view(), name="wizard_children"),
    url(r'^activities/$', ActivityListView.as_view(), name='wizard_activities'),
    url(r'^confirm/$', RegisteredActivitiesListView.as_view(), name="wizard_confirm"),
    url(r'^billing/$', WizardBillingView.as_view(), name="wizard_billing"),
)
