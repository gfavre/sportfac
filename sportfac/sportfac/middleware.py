from django.conf import settings
from django.db import connection
from django.http import Http404
from django.utils import timezone

from django_tenants.middleware import TenantMiddleware
from backend.models import Domain
from backend.dynamic_preferences_registry import tenant_preferences_registry


class RegistrationOpenedMiddleware(object):
    def process_request(self, request):
        preferences = request.tenant.preferences.by_name()
        start = request.tenant.preferences.by_name()['START_REGISTRATION']
        end = request.tenant.preferences.by_name()['END_REGISTRATION']
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


class VersionMiddleware(TenantMiddleware):
    def hostname_from_request(self, request):
        if settings.VERSION_SESSION_NAME in request.session:
            return request.session.get(settings.VERSION_SESSION_NAME)
        else:
            domain = Domain.objects.filter(is_current=True).first()
            request.session[settings.VERSION_SESSION_NAME] = domain.domain
            return domain.domain
    
    def process_request(self, request): 
        try:
            super(VersionMiddleware, self).process_request(request)
        except Http404:
            del request.session[settings.VERSION_SESSION_NAME]
            return super(VersionMiddleware, self).process_request(request)