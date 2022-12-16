from django.urls import path

from .views.register import SlotsView, SuccessfulRegister


app_name = "appointments"

urlpatterns = [
    path("success", SuccessfulRegister.as_view(), name="success"),
    path("", SlotsView.as_view(), name="register"),
]
