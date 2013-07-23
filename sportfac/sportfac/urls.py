from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='home.html'), name="home"),
    
    url(r'^terms$', TemplateView.as_view(template_name='terms.html'), name="terms"),

    url(r'^api/', include('api.urls')),
    url(r'^activities/', include('activities.urls')),
    url(r'^account/', include('profiles.urls')),
    url(r'^contact/', include('contact.urls')),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
