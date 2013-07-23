from django.conf.urls import patterns, url
from django.views.generic import TemplateView

from .views import ContactView

urlpatterns = patterns('',
    url(r'^$', ContactView.as_view(), name='contact'),
    url(r'^thanks/$', view=TemplateView.as_view(template_name='contact/thanks.html'), name="contact_thanks")
) 