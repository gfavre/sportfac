from django.conf import settings

from sportfac.utils import TenantTestCase


class WellKnownRootPathRedirectsTest(TenantTestCase):
    """Browsers probe these well-known paths at the domain root on their own, unprompted
    by any <link> tag in our templates - each used to fall through to Django's generic
    404 handling (a full request through every middleware) instead of a cheap redirect.
    permanent=True (301) additionally lets the browser cache the redirect itself and stop
    asking Django at all on later visits."""

    def _assert_permanent_redirect(self, path, expected_target):
        response = self.tenant_client.get(path)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.url, expected_target)

    def test_favicon(self):
        self._assert_permanent_redirect("/favicon.ico", settings.STATIC_URL + "img/favicon.ico")

    def test_apple_touch_icon_variants_redirect_to_the_single_shipped_icon(self):
        target = settings.STATIC_URL + "img/apple-touch-icon.png"
        for path in (
            "/apple-touch-icon.png",
            "/apple-touch-icon-precomposed.png",
            "/apple-touch-icon-120x120.png",
            "/apple-touch-icon-120x120-precomposed.png",
            "/apple-touch-icon-152x152.png",
            "/apple-touch-icon-152x152-precomposed.png",
        ):
            with self.subTest(path=path):
                self._assert_permanent_redirect(path, target)

    def test_safari_pinned_tab(self):
        self._assert_permanent_redirect("/safari-pinned-tab.svg", settings.STATIC_URL + "img/safari-pinned-tab.svg")
