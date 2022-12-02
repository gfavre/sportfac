from __future__ import absolute_import
from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib import sitemaps
from django.urls import reverse

from .views import ContactView

class Sitemap(sitemaps.Sitemap):
    def items(self):
        return ['contact']
    
    def location(self, item):
        return reverse(item)



urlpatterns = [
    url(r'^$', ContactView.as_view(), name='contact'),
    url(r'^thanks/$', view=TemplateView.as_view(template_name='contact/thanks.html'), name="contact_thanks")
]