from __future__ import absolute_import
from django.conf.urls import url

from .views import BillingView, BillDetailView, RegistrationDeleteView, ChildrenListView, SummaryView


urlpatterns = [
    url(r'^children/$', ChildrenListView.as_view(), name="registrations_children"),
    url(r'^payment/$', BillingView.as_view(), name="registrations_billing"),
    url(r'^payment/(?P<pk>\d+)$', BillDetailView.as_view(), name="registrations_bill_detail"),
    url(r'^summary/$', SummaryView.as_view(), name="registrations_registered_activities"),
    url(r'^cancel/(?P<pk>\d+)$', RegistrationDeleteView.as_view(), name="cancel-registration"),
]
