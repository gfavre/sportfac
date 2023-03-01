from django.conf import settings
from django.http import Http404
from django.utils import timezone

from backend.models import Domain
from django_tenants.middleware import TenantMainMiddleware


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
        response = self.get_response(request)

        return response


class VersionMiddleware(TenantMainMiddleware):
    @staticmethod
    def hostname_from_request(request):
        if settings.VERSION_SESSION_NAME in request.session:
            return request.session.get(settings.VERSION_SESSION_NAME)
        else:
            domain = Domain.objects.filter(is_current=True).first()
            request.session[settings.VERSION_SESSION_NAME] = domain.domain
            return domain.domain

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
