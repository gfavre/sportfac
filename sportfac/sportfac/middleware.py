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
        if pinned_domain and pinned_domain != production_domain and getattr(request.user, "is_kepchup_staff", False):
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
