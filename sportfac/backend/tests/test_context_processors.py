"""dynamic_preferences_context (sportfac/context_processors.py) runs on every rendered
page across the whole site (registered in TEMPLATES, sportfac/settings/base.py) - it used
to fetch 8 preferences one at a time (each its own single-key cache round trip, two of
them fetched twice for no reason), instead of the one batched round trip
PreferencesManager.all() already provides. These tests cover both correctness (the
rewrite must return the exact same values) and the query-count regression it fixes.
"""
from datetime import timedelta

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils.timezone import now
from dynamic_preferences.registries import global_preferences_registry

from sportfac.context_processors import dynamic_preferences_context
from sportfac.utils import TenantTestCase


class DynamicPreferencesContextTest(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.preferences = global_preferences_registry.manager()
        # .all() (called by dynamic_preferences_context and by this test) reads every
        # registered global preference, not just the handful set below - warm every row
        # into the DB now so the "single query" assertion isn't at the mercy of whichever
        # preferences some other test happened to touch first (dynamic_preferences creates
        # a row lazily on first access, which would otherwise show up as extra INSERTs).
        self.preferences.all()

    def _set_and_clear_cache(self, **values):
        for key, value in values.items():
            self.preferences[key] = value
        # Setting a preference already writes through to the cache - clear it so the
        # context processor is exercised against a genuinely cold cache, same as a
        # worker process would see after the default 5-minute cache TTL expires.
        cache.clear()

    def test_returns_expected_values(self):
        start = now() - timedelta(days=1)
        end = now() + timedelta(days=1)
        self._set_and_clear_cache(
            **{
                "phase__OTHER_START_REGISTRATION": start,
                "phase__OTHER_END_REGISTRATION": end,
                "site__SITE_NAME": "Test Site",
                "PERIOD_NAME": "2026-2027",
                "MAX_REGISTRATIONS": 5,
                "site__INSTRUCTOR_FALLBACK_PHONE": "+41 79 000 00 00",
            }
        )

        context = dynamic_preferences_context(request=None)

        self.assertEqual(context["site_name"], "Test Site")
        self.assertEqual(context["preferences_period_name"], "2026-2027")
        self.assertEqual(context["MAX_REGISTRATIONS_PER_CHILD"], 5)
        self.assertEqual(context["INSTRUCTOR_FALLBACK_PHONE"], "+41 79 000 00 00")
        self.assertEqual(context["preference_other_instance_start_registration"], start)
        self.assertEqual(context["preference_other_instance_end_registration"], end)
        # start is in the past and end is in the future -> phase 2 (registrations open)
        self.assertEqual(context["other_instance_phase"], 2)
        self.assertTrue(context["other_instance_started_registrations"])

    def test_phase_before_other_instance_registration_opened(self):
        self._set_and_clear_cache(
            **{
                "phase__OTHER_START_REGISTRATION": now() + timedelta(days=1),
                "phase__OTHER_END_REGISTRATION": now() + timedelta(days=2),
            }
        )
        context = dynamic_preferences_context(request=None)
        self.assertEqual(context["other_instance_phase"], 1)
        self.assertFalse(context["other_instance_started_registrations"])

    def test_phase_after_other_instance_registration_closed(self):
        self._set_and_clear_cache(
            **{
                "phase__OTHER_START_REGISTRATION": now() - timedelta(days=2),
                "phase__OTHER_END_REGISTRATION": now() - timedelta(days=1),
            }
        )
        context = dynamic_preferences_context(request=None)
        self.assertEqual(context["other_instance_phase"], 3)
        self.assertFalse(context["other_instance_started_registrations"])

    @staticmethod
    def _real_query_count(ctx):
        # django_tenants issues its own "SET search_path" ahead of each real query on
        # this connection - schema bookkeeping outside what this fix controls.
        return len([q for q in ctx.captured_queries if "SET search_path" not in q["sql"]])

    def test_cold_cache_issues_a_single_query_regardless_of_key_count(self):
        cache.clear()
        with CaptureQueriesContext(connection) as ctx:
            dynamic_preferences_context(request=None)
        self.assertEqual(self._real_query_count(ctx), 1)

    def test_warm_cache_issues_no_query(self):
        dynamic_preferences_context(request=None)  # warm the cache
        with CaptureQueriesContext(connection) as ctx:
            dynamic_preferences_context(request=None)
        self.assertEqual(self._real_query_count(ctx), 0)
