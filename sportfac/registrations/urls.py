from django.conf.urls import url, include
from django.contrib.auth import views as auth_views

from .views import BillingView, BillDetailView, ChildrenListView, SummaryView


urlpatterns = [
    url(r'^children/$', ChildrenListView.as_view(), name="registrations_children"),
    url(r'^payement/$', BillingView.as_view(), name="registrations_billing"),
    url(r'^payement/(?P<pk>\d+)$', BillDetailView.as_view(), name="registrations_bill_detail"),
    url(r'^summary/$', SummaryView.as_view(), name="registrations_registered_activities"),
]
