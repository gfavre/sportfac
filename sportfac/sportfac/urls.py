from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import FlatPageSitemap, GenericSitemap
from django.views.generic import TemplateView, RedirectView
from django.core.urlresolvers import reverse

import autocomplete_light

from activities.urls import sitemap as activity_sitemap
from contact.urls import Sitemap as ContactSitemap

autocomplete_light.autodiscover()
admin.autodiscover()


sitemaps = {
    'flatpages': FlatPageSitemap,
    'activities': activity_sitemap,
    'contact': ContactSitemap,
}
class TextPlainView(TemplateView):
  def render_to_response(self, context, **kwargs):
    return super(TextPlainView, self).render_to_response(
      context, content_type='text/plain', **kwargs)


urlpatterns = patterns('',
    #url(r'^$', TemplateView.as_view(template_name='home.html'), name="home"),
    #url(r'^terms$', TemplateView.as_view(template_name='terms.html'), name="terms"),
    url(r'^api/', include('api.urls')),
    url(r'^activities/', include('activities.urls')),
    url(r'^account/', include('profiles.urls')),
    url(r'^backend/', include('backend.urls')),
    url(r'^contact/', include('contact.urls')),
    url(r'^ckeditor/', include('ckeditor.urls')),
    
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', TextPlainView.as_view(template_name='robots.txt')),
    url(r'^humans\.txt$', TextPlainView.as_view(template_name='humans.txt')),
    url(r'^favicon\.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico')),
    
    url(r'^wizard/', include('sportfac.wizardurls')),
    
    url(r'404$', TemplateView.as_view(template_name='404.html')),
    url(r'500$', TemplateView.as_view(template_name='500.html')),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/autocomplete/', include('autocomplete_light.urls')),
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