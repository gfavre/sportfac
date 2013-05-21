from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='base.html')),
    url(r'^api/', include('api.urls')),
    url(r'^activities/', include('activities.urls')),

    url(r'^login/$', 'django.contrib.auth.views.login', name="login"),
    url(r'^logout$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name="logout"),
    url(r'^admin/', include(admin.site.urls)),
)
