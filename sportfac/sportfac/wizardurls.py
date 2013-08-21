from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

from activities.views import ActivityListView
from profiles.views import AccountView, MyRegistrationView, ChildrenListView, BillingView, RegisteredActivitiesListView


urlpatterns = patterns('',
    url(r'^register/$', MyRegistrationView.as_view(wizard=True), name='wizard_register'),
    url(r'^account/$', AccountView.as_view(wizard=True), name='wizard_account'),
    url(r'^children/$', ChildrenListView.as_view(wizard=True), name="wizard_children"),
    url(r'^activities/$', ActivityListView.as_view(wizard=True), name='wizard_activities'),
    url(r'^confirm/$', RegisteredActivitiesListView.as_view(wizard=True), name="wizard_confirm"),
    url(r'^billing/$', BillingView.as_view(wizard=True), name="wizard_billing"),
)
