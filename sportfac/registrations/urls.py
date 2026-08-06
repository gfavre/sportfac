from django.urls import path

from .views.user import BillDetailView
from .views.user import BillingView
from .views.user import BillPdfView
from .views.user import ChildrenListView
from .views.user import RegistrationDeleteView
from .views.user import SummaryView


app_name = "registrations"
urlpatterns = [
    path("children/", ChildrenListView.as_view(), name="registrations_children"),
    path("payment/", BillingView.as_view(), name="registrations_billing"),
    path("payment/<int:pk>", BillDetailView.as_view(), name="registrations_bill_detail"),
    path("payment/<int:pk>/pdf", BillPdfView.as_view(), name="registrations_bill_pdf"),
    path("summary/", SummaryView.as_view(), name="registrations_registered_activities"),
    path("cancel/<int:pk>", RegistrationDeleteView.as_view(), name="cancel-registration"),
]
