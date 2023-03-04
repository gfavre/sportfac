from django.contrib import sitemaps
from django.urls import path, reverse
from django.views.generic import TemplateView

from .views import ContactView


class Sitemap(sitemaps.Sitemap):
    def items(self):
        return ["contact:contact"]

    def location(self, item):
        return reverse(item)


app_name = "contact"

urlpatterns = [
    path("", ContactView.as_view(), name="contact"),
    path(
        "thanks/",
        view=TemplateView.as_view(template_name="contact/thanks.html"),
        name="contact_thanks",
    ),
]
