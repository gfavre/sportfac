import time

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django_tenants.middleware import TenantMainMiddleware

from backend.models import Domain


# Module-level (per gunicorn worker process), not django.core.cache: the "default" cache
# backend keys everything through django_tenants.cache.make_key, which prefixes by whatever
# schema the DB connection is CURRENTLY on - and this lookup runs before the schema switch
# it's itself deciding (same class of ordering issue as the is_kepchup_staff fix noted
# below), so a tenant-prefixed cache key here would just miss constantly across requests
# landing on different current schemas instead of ever actually being shared.
#
# Which tenant is production changes at most a couple of times a year (backend/tasks.py's
# update_current_tenant, or a manager triggering backend/views/year_views.py's
# ChangeYearFormView) - both call Domain.save() on the way, which backend/signals.py hooks
# with a post_save receiver calling invalidate_production_domain_cache() below, so the
# worker process that actually performs the switch picks up the new value on its very next
# request. The 24h TTL is a backstop, not the primary mechanism: a signal only fires in the
# process that ran the save, so gunicorn's *other* worker processes won't see it - they'd
# otherwise serve the old value until their own natural recycling (--max-requests) or the
# next deploy. Long enough that it's essentially free the rest of the year, short enough
# that a quiet worker that missed the signal can't drift for that long.
_PRODUCTION_DOMAIN_CACHE_SECONDS = 24 * 60 * 60
_production_domain_cache = {"value": None, "expires_at": 0.0}


def _get_production_domain():
    now = time.monotonic()
    if now >= _production_domain_cache["expires_at"]:
        _production_domain_cache["value"] = Domain.objects.filter(is_current=True).first().domain
        _production_domain_cache["expires_at"] = now + _PRODUCTION_DOMAIN_CACHE_SECONDS
    return _production_domain_cache["value"]


def invalidate_production_domain_cache():
    """Called by backend.signals on Domain.save()/delete() - forces the next call to
    _get_production_domain() in this process to re-hit the DB instead of waiting out the
    24h backstop TTL."""
    _production_domain_cache["expires_at"] = 0.0


class RegistrationOpenedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The health check must be able to report "this tenant's data is broken"
        # (e.g. a missing/corrupted preference) rather than crash on it before ever
        # reaching its own try/except'd checks - see sportfac/health.py. Doesn't cover
        # every failure mode (VersionMiddleware/TenantMainMiddleware, earlier in the
        # chain, still needs the DB connection itself to resolve the tenant at all -
        # a fully-down DB still surfaces as a plain 500 there, not this view's JSON).
        if request.path == "/_health-kc/":
            return self.get_response(request)
        preferences = request.tenant.preferences.by_name()
        start = preferences["START_REGISTRATION"]
        end = preferences["END_REGISTRATION"]
        now = timezone.now()

        request.PHASE = 1
        request.REGISTRATION_OPENED = False
        if start <= now <= end:
            request.PHASE = 2
            request.REGISTRATION_OPENED = True
        elif now > end:
            request.PHASE = 3
        request.REGISTRATION_START = start
        request.REGISTRATION_END = end
        return self.get_response(request)


class VersionMiddleware(TenantMainMiddleware):
    @staticmethod
    def hostname_from_request(request):
        production_domain = _get_production_domain()
        pinned_domain = request.session.get(settings.VERSION_SESSION_NAME)
        # Only kepchup staff previewing another period may stay pinned to a non-production
        # tenant - everyone else always resolves to the live production one, even if their
        # session still carries a pin from a previous visit under a since-retired
        # production period. Without this, a family who last visited during the *previous*
        # season could keep landing on that now-closed, non-production tenant (with the
        # staff-only "not production" banner) indefinitely: `log_everyone_out` is meant to
        # clear that stale pin on every season switch by deleting all sessions, but
        # silently no-ops in production, where SESSION_ENGINE is cache-backed while it
        # deletes from the unrelated DB-backed Session model.
        #
        # Deliberately NOT using FamilyUser.is_kepchup_staff here: its is_instructor check
        # queries `activities.CoursesInstructors`, a tenant-scoped table - but this method
        # IS what determines which tenant's schema to switch to, so it runs before that
        # switch happens. Querying a tenant-scoped table here hits whatever schema the DB
        # connection was last left on (`public` on a fresh one), crashing with
        # "relation ... does not exist" - hit in production for any logged-in, non-staff
        # visitor (2026-08-23, e.g. a plain favicon.ico request carrying their session
        # cookie). is_manager/is_restricted_manager/is_superuser are plain fields on
        # FamilyUser (profiles is a SHARED_APPS model, its table exists regardless of the
        # current schema) - safe here. An instructor-only account (no other role) will no
        # longer stay pinned to a preview period through this middleware; ChangeYearFormView
        # itself is unaffected, since normal views already run with the schema resolved.
        is_privileged = request.user.is_authenticated and (
            request.user.is_manager or request.user.is_restricted_manager or request.user.is_superuser
        )
        if pinned_domain and pinned_domain != production_domain and is_privileged:
            return pinned_domain
        if pinned_domain != production_domain:
            request.session[settings.VERSION_SESSION_NAME] = production_domain
        return production_domain

    def __call__(self, request):
        response = None
        try:
            if hasattr(self, "process_request"):
                response = self.process_request(request)
            response = response or self.get_response(request)
            if hasattr(self, "process_response"):
                response = self.process_response(request, response)
        except Http404:
            del request.session[settings.VERSION_SESSION_NAME]
        return response
