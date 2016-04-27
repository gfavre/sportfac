from django.conf import settings
from django.db import connection
from django.utils import timezone

from constance.admin import config
from django_tenants.middleware import TenantMiddleware

class RegistrationOpenedMiddleware(object):
    def process_request(self, request):
        start = config.START_REGISTRATION
        end = config.END_REGISTRATION
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
        return request.COOKIES.get(settings.VERSION_COOKIE_NAME, settings.DEFAULT_TENANT_NAME)