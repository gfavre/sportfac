from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static

from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    #url(r'^$', TemplateView.as_view(template_name='home.html'), name="home"),
    #url(r'^terms$', TemplateView.as_view(template_name='terms.html'), name="terms"),
    url(r'^api/', include('api.urls')),
    url(r'^activities/', include('activities.urls')),
    url(r'^account/', include('profiles.urls')),
    url(r'^contact/', include('contact.urls')),
    url(r'^ckeditor/', include('ckeditor.urls')),
    
    url(r'^wizard/', include('sportfac.wizardurls')),
    
    url(r'404$', TemplateView.as_view(template_name='404.html')),
    url(r'500$', TemplateView.as_view(template_name='500.html')),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += patterns('django.contrib.flatpages.views',
    url(r'^$', 'flatpage', {'url': '/'}, name='home'),
    url(r'^reglement/$', 'flatpage', {'url': '/reglement/'}, name='terms'),
)




if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)