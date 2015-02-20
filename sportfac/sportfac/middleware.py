from django.utils import timezone

from constance.admin import config


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

