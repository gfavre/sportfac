"""Tests for backend.signals - tenant cache invalidation must work regardless of cache backend."""
from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase

from backend.signals import _invalidate_all_tenant_caches
from backend.signals import clear_production_domain_cache


class InvalidateTenantCachesTests(SimpleTestCase):
    def test_does_not_raise_when_cache_backend_lacks_delete_pattern(self):
        # LocMemCache (used in dev/test settings) has no delete_pattern, unlike django-redis.
        self.assertFalse(hasattr(cache, "delete_pattern"))
        _invalidate_all_tenant_caches()

    def test_uses_delete_pattern_when_available(self):
        fake_cache = mock.Mock(spec=["delete_pattern"])
        with mock.patch("backend.signals.cache", fake_cache):
            _invalidate_all_tenant_caches()
        fake_cache.delete_pattern.assert_called_once_with("tenants_context_user_*")

    def test_falls_back_to_clear_without_delete_pattern(self):
        fake_cache = mock.Mock(spec=["clear"])
        with mock.patch("backend.signals.cache", fake_cache):
            _invalidate_all_tenant_caches()
        fake_cache.clear.assert_called_once()


class ClearProductionDomainCacheTests(SimpleTestCase):
    """clear_production_domain_cache is the receiver, not the invalidation logic itself
    (that's sportfac.middleware.invalidate_production_domain_cache, covered by its own
    tests) - this only needs to prove the receiver calls it."""

    def test_calls_invalidate_production_domain_cache(self):
        with mock.patch("sportfac.middleware.invalidate_production_domain_cache") as mock_invalidate:
            clear_production_domain_cache(sender=None)
        mock_invalidate.assert_called_once()
