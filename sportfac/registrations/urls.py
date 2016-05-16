from django.conf.urls import url, include
from django.contrib.auth import views as auth_views

from .views import BillingView, ChildrenListView, SummaryView


urlpatterns = [
    url(r'^children/$', ChildrenListView.as_view(), name="registrations_children"),
    url(r'^payement/$', BillingView.as_view(), name="registrations_billing"),
    url(r'^summary/$', SummaryView.as_view(), name="registrations_registered_activities"),
]
