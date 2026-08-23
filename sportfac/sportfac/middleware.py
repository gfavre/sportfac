from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django_tenants.middleware import TenantMainMiddleware

from backend.models import Domain


class RegistrationOpenedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
        production_domain = Domain.objects.filter(is_current=True).first().domain
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
