from django.urls import path

from django.views.generic import TemplateView
from .views import WhistleView


app_name = "nyonmarens"

urlpatterns = [
    path("", WhistleView.as_view(), name="whistle"),
    path("merci", TemplateView.as_view(template_name="nyonmarens/thanks.html"), name="whistle_thanks"),
]
