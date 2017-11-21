from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps import views as sitemapviews
from django.contrib.flatpages import views as flatviews
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.views.generic import TemplateView, RedirectView
from django.views.static import serve

from ckeditor_uploader import views as ckeditor_views

from backend.utils import manager_required

from activities.urls import sitemap as activity_sitemap
from contact.urls import Sitemap as ContactSitemap

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


urlpatterns = [
    url(r'^$', flatviews.flatpage, {'url': '/'}, name='home'),
    url(r'^reglement/$', flatviews.flatpage, {'url': '/reglement/'}, name='terms'),
    url(r'^protection-des-donnees/$', flatviews.flatpage, {'url': '/protection-des-donnees/'}, name='privacy'),

    url(r'^api/', include('api.urls', namespace="api")),
    url(r'^activities/', include('activities.urls', namespace="activities")),
    url(r'^account/login$', auth_views.login, name='login'),
    url(r'^account/', include('profiles.urls')),
    url(r'^backend/', include('backend.urls', namespace="backend", app_name="backend")),
    url(r'^contact/', include('contact.urls')),
    url(r'^registrations/', include('registrations.urls')),

    url(r'^sitemap\.xml$', sitemapviews.sitemap, {'sitemaps': sitemaps}),
    url(r'^robots\.txt$', TextPlainView.as_view(template_name='robots.txt')),
    url(r'^humans\.txt$', TextPlainView.as_view(template_name='humans.txt')),
    url(r'^favicon\.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'img/favicon.ico')),

    url(r'^wizard/', include('sportfac.wizardurls')),

    url(r'404$', TemplateView.as_view(template_name='404.html')),
    url(r'500$', TemplateView.as_view(template_name='500.html')),

    url(r'^ckeditor/upload/', manager_required(ckeditor_views.upload), name='ckeditor_upload'),
    url(r'^ckeditor/browse/', manager_required(ckeditor_views.browse), name='ckeditor_browse'),

    #url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
]

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT
        }),
    ]
