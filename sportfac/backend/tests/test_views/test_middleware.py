from unittest import mock

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.db import connection
from django.test.client import RequestFactory

from backend.models import Domain
from profiles.tests.factories import FamilyUserFactory
from sportfac.middleware import VersionMiddleware
from sportfac.middleware import _get_production_domain
from sportfac.middleware import invalidate_production_domain_cache
from sportfac.utils import TenantTestCase
from sportfac.utils import process_request_for_middleware


class HostnameFromRequestTest(TenantTestCase):
    """VersionMiddleware.hostname_from_request runs *before* the tenant schema is
    switched (it's what decides which schema to switch to) - it must never touch a
    tenant-scoped table, or it crashes for whichever schema the DB connection happens
    to still be on. Regression test for the 2026-08-23 incident: any logged-in,
    non-staff visitor's request (even a plain favicon.ico carrying their session
    cookie) crashed with `relation "activities_coursesinstructors" does not exist`,
    because `FamilyUser.is_kepchup_staff` queries that tenant-scoped table via
    `is_instructor`.
    """

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.production_domain = self.tenant.domains.first().domain

    def _request(self, user):
        request = self.factory.get("/")
        process_request_for_middleware(request, SessionMiddleware)
        request.session["period"] = "some-other-stale-domain"
        request.user = user
        return request

    def _call_on_public_schema(self, request):
        # hostname_from_request runs *before* the tenant switch it decides on - the real
        # incident happened with the DB connection still sitting on `public` (fresh
        # connection, or whatever a previous request left it on). Reproduce that
        # precondition explicitly, rather than relying on whatever schema the test
        # harness happens to already be on (which stays on this tenant's own schema and
        # would silently hide the bug - it was confirmed to reproduce this way, and not
        # by leaving the harness's default schema in place).
        connection.set_schema_to_public()
        try:
            return VersionMiddleware.hostname_from_request(request)
        finally:
            connection.set_tenant(self.tenant)

    def test_anonymous_visitor_resolves_to_production_without_crashing(self):
        hostname = self._call_on_public_schema(self._request(AnonymousUser()))
        self.assertEqual(hostname, self.production_domain)

    def test_plain_family_resolves_to_production_without_crashing(self):
        family = FamilyUserFactory(is_manager=False, is_restricted_manager=False, is_superuser=False)
        hostname = self._call_on_public_schema(self._request(family))
        self.assertEqual(hostname, self.production_domain)

    def test_manager_keeps_their_preview_pin(self):
        manager = FamilyUserFactory(is_manager=True)
        request = self._request(manager)
        hostname = self._call_on_public_schema(request)
        self.assertEqual(hostname, "some-other-stale-domain")


class ProductionDomainCacheTest(TenantTestCase):
    """_get_production_domain() (sportfac/middleware.py) caches the current production
    domain per worker process to avoid a Domain query on every single request. The cache
    is module-level, not per-test, so every test here must start from a known state.
    """

    def setUp(self):
        super().setUp()
        invalidate_production_domain_cache()

    def tearDown(self):
        super().tearDown()
        invalidate_production_domain_cache()

    def test_first_call_hits_the_database(self):
        with mock.patch("sportfac.middleware.Domain.objects.filter", wraps=Domain.objects.filter) as spy:
            domain = _get_production_domain()
        spy.assert_called_once()
        self.assertEqual(domain, self.tenant.domains.first().domain)

    def test_second_call_does_not_hit_the_database(self):
        _get_production_domain()
        with mock.patch("sportfac.middleware.Domain.objects.filter", wraps=Domain.objects.filter) as spy:
            _get_production_domain()
        spy.assert_not_called()

    def test_a_reasonable_update_is_picked_up_on_the_very_next_call(self):
        # "Reasonable update": a real production switch, the same two-save sequence
        # backend/tasks.py's update_current_tenant and year_views.py's
        # ChangeYearFormView.form_valid both perform - old domain unset, new one set,
        # each via a plain .save() (which is what fires the invalidating signal).
        original_domain = _get_production_domain()

        old_domain = Domain.objects.get(domain=original_domain)
        old_domain.is_current = False
        old_domain.save()
        new_domain = Domain.objects.create(domain="new-production.example.com", tenant=self.tenant, is_current=True)

        self.assertEqual(_get_production_domain(), new_domain.domain)
        self.assertNotEqual(_get_production_domain(), original_domain)
