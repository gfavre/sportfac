from django.utils import timezone

from constance.admin import config


class RegistrationOpenedMiddleware(object):
    def process_request(self, request):
        start = config.START_REGISTRATION
        end = config.END_REGISTRATION
        now = timezone.now()
        request.REGISTRATION_OPENED = start <= now <= end
        request.REGISTRATION_START = start
        request.REGISTRATION_END = end

