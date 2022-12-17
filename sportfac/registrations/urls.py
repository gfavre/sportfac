from django.urls import path

from .views import (BillDetailView, BillingView, ChildrenListView, RegistrationDeleteView,
                    SummaryView)


app_name = "registrations"
urlpatterns = [
    path("children/", ChildrenListView.as_view(), name="registrations_children"),
    path("payment/", BillingView.as_view(), name="registrations_billing"),
    path("payment/<int:pk>", BillDetailView.as_view(), name="registrations_bill_detail"),
    path("summary/", SummaryView.as_view(), name="registrations_registered_activities"),
    path("cancel/<int:pk>", RegistrationDeleteView.as_view(), name="cancel-registration"),
]
