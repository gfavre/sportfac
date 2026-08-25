from ckeditor_uploader import views as ckeditor_views
from django.conf import settings
from django.contrib import admin
from django.contrib.flatpages import views as flatviews
from django.contrib.flatpages.sitemaps import FlatPageSitemap
from django.contrib.sitemaps import views as sitemapviews
from django.http import HttpResponsePermanentRedirect
from django.urls import include
from django.urls import path
from django.urls import re_path
from django.views.generic import RedirectView
from django.views.generic import TemplateView
from django.views.static import serve
from impersonate import views as impersonate_views

from activities.urls import sitemap as activity_sitemap
from backend.utils import manager_required
from contact.urls import Sitemap as ContactSitemap
from payments.views import DatatransWebhookView
from payments.views import NewDatatransTransactionView
from payments.views import NewPostfinanceTransactionView
from payments.views import PostfinanceWebhookView

from .views import health_check
from .views import impersonate as impersonate_view


admin.autodiscover()

sitemaps = {
    "flatpages": FlatPageSitemap,
    "activities": activity_sitemap,
    "contact": ContactSitemap,
}


def redirect_wizard2(request, path: str = ""):
    """
    Redirect /wizard2/* → /wizard/*, preserving any URL prefix such as /hiver/.
    """
    prefix = ""
    # Exemple: path_info = "/wizard2/test/" ou "/hiver/wizard2/test/"

    if settings.FORCE_SCRIPT_NAME and request.path.startswith(settings.FORCE_SCRIPT_NAME):
        prefix = settings.FORCE_SCRIPT_NAME

    return HttpResponsePermanentRedirect(f"{prefix}/wizard/{path}")


class TextPlainView(TemplateView):
    def render_to_response(self, context, **kwargs):
        return super().render_to_response(context, content_type="text/plain", **kwargs)


if settings.KEPCHUP_USE_SSO:
    from profiles.client import KepchupClient

    sso_client = KepchupClient(settings.SSO_SERVER, settings.SSO_PUBLIC_KEY, settings.SSO_PRIVATE_KEY)
    if settings.KEPCHUP_SPLASH_PAGE:
        urlpatterns = [
            path("client/", include(sso_client.get_urls())),
            path("", flatviews.flatpage, {"url": "/splash/"}, name="splash"),
            path("accueil/", flatviews.flatpage, {"url": "/"}, name="home"),
        ]
    else:
        urlpatterns = [
            path("client/", include(sso_client.get_urls())),
            path("", flatviews.flatpage, {"url": "/home"}, name="home"),
        ]

else:
    if settings.KEPCHUP_SPLASH_PAGE:
        urlpatterns = [
            path("", flatviews.flatpage, {"url": "/splash/"}, name="splash"),
            path("accueil/", flatviews.flatpage, {"url": "/"}, name="home"),
        ]
    else:
        urlpatterns = [
            path("", flatviews.flatpage, {"url": "/"}, name="home"),
        ]

if settings.KEPCHUP_USE_APPOINTMENTS:
    urlpatterns += [path("rendez-vous/", include("appointments.urls", namespace="appointments"))]


if settings.KEPCHUP_ACTIVATE_NYON_MARENS:
    urlpatterns += [path("nyon-marens/", include("nyonmarens.urls", namespace="nyonmarens"))]

urlpatterns += [
    path("reglement/", flatviews.flatpage, {"url": "/reglement/"}, name="terms"),
    path(
        "protection-des-donnees/",
        flatviews.flatpage,
        {"url": "/protection-des-donnees/"},
        name="privacy",
    ),
    path("api/", include("api.urls", namespace="api")),
    path("activities/", include("activities.urls", namespace="activities")),
    path("account/", include("profiles.urls")),
    path("backend/", include("backend.urls", namespace="backend")),
    path("ckeditor/upload/", manager_required(ckeditor_views.upload), name="ckeditor_upload"),
    path("ckeditor/browse/", manager_required(ckeditor_views.browse), name="ckeditor_browse"),
    path("contact/", include("contact.urls")),
    path(
        "datatrans/new-transaction/<int:invoice_id>/",
        NewDatatransTransactionView.as_view(),
        name="datatrans-new-transaction",
    ),
    path("datatrans/", DatatransWebhookView.as_view(), name="datatrans_webhook"),
    # Unauthenticated on purpose (LB/uptime-monitor probes can't log in) - path is not
    # linked from anywhere, but that's not the security boundary: the response itself
    # never contains raw numbers or error details, see sportfac/health.py.
    path("_health-kc/", health_check, name="health-check"),
    # permanent=True (301): browsers probe these well-known root paths on their own,
    # unprompted by any <link> tag, on every first visit of a session - a 301 lets the
    # browser cache the redirect target itself and stop re-asking Django for it at all on
    # subsequent visits, unlike the plain 302 this used to be. apple-touch-icon's sized/
    # precomposed variants all redirect to the one icon each theme actually ships - some of
    # these targets may 404 themselves (e.g. safari-pinned-tab.svg isn't provided by every
    # theme), but even that 404 is now served straight off disk by Apache's /static/ Alias,
    # not proxied through the full Django/gunicorn request cycle like it was before.
    path(
        "favicon.ico",
        RedirectView.as_view(url=settings.STATIC_URL + "img/favicon.ico", permanent=True),
    ),
    path(
        "apple-touch-icon.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "apple-touch-icon-precomposed.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "apple-touch-icon-120x120.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "apple-touch-icon-120x120-precomposed.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "apple-touch-icon-152x152.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "apple-touch-icon-152x152-precomposed.png",
        RedirectView.as_view(url=settings.STATIC_URL + "img/apple-touch-icon.png", permanent=True),
    ),
    path(
        "safari-pinned-tab.svg",
        RedirectView.as_view(url=settings.STATIC_URL + "img/safari-pinned-tab.svg", permanent=True),
    ),
    path("humans.txt", TextPlainView.as_view(template_name="humans.txt")),
    path("impersonate/<path:uid>/", impersonate_view, name="impersonate-start"),
    path("impersonate-stop/", impersonate_views.stop_impersonate, name="impersonate-stop"),
    path(
        "postfinance/new-transaction/<int:invoice_id>/",
        NewPostfinanceTransactionView.as_view(),
        name="postfinance-new-transaction",
    ),
    path("postfinance/", PostfinanceWebhookView.as_view(), name="postfinance_webhook"),
    path("registrations/", include("registrations.urls")),
    path("robots.txt", TextPlainView.as_view(template_name="robots.txt")),
    path("select2/", include("django_select2.urls")),
    path("sitemap.xml", sitemapviews.sitemap, {"sitemaps": sitemaps}),
    re_path(r"^wizard2/(?P<path>.*)$", redirect_wizard2, name="redirect-wizard2"),
    path("wizard/", include("wizard.urls")),
    path(settings.ADMIN_URL, admin.site.urls),
]

handler404 = "sportfac.views.not_found"
handler500 = "sportfac.views.server_error"


if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar

    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
        path("404", TemplateView.as_view(template_name="404.html")),
        path("500", TemplateView.as_view(template_name="500.html")),
        path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
