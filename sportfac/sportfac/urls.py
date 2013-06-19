from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='home.html'), name="home"),
    
    url(r'^test', TemplateView.as_view(template_name='wizard.html')),
    
    url(r'^api/', include('api.urls')),
    url(r'^activities/', include('activities.urls')),
    url(r'^account/', include('profiles.urls')),
    
    url(r'^admin/', include(admin.site.urls)),
)
