from datetime import datetime

from braces.views import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from impersonate.decorators import allowed_user_required
from impersonate.helpers import check_allow_for_user
from impersonate.helpers import get_redir_path
from impersonate.signals import session_begin

from profiles.models import FamilyUser

from .health import CRITICAL
from .health import overall_level
from .health import run_checks


class OpenedPeriodMixin:
    """Raise a 403 status when period is not opened"""

    def dispatch(self, request, *args, **kwargs):
        """Called before get or post methods"""
        if request.REGISTRATION_OPENED:
            return super().dispatch(request, *args, **kwargs)
        raise PermissionDenied


class PhaseForbiddenMixin(LoginRequiredMixin):
    forbidden_phases = None

    def get_forbidden_phases(self):
        if self.forbidden_phases is None:
            raise ImproperlyConfigured(
                f'{self.__class__.__name__} requires the "forbidden_phases" attribute to be set.'
            )
        return self.forbidden_phases

    def check_phase(self, request):
        current_phase = request.PHASE
        return current_phase not in self.get_forbidden_phases()

    def dispatch(self, request, *args, **kwargs):
        """
        Check to see if the request.PHASE is compatible
        """
        correct_phase = self.check_phase(request)
        if not correct_phase:
            if self.raise_exception:
                raise PermissionDenied  # Return a 403
            return redirect_to_login(request.get_full_path(), self.get_login_url(), self.get_redirect_field_name())
        return super().dispatch(request, *args, **kwargs)


class CSVMixin:
    def get_csv_filename(self):
        return NotImplementedError

    def write_csv(self, filelike):
        return NotImplementedError

    # noinspection PyUnusedLocal
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = HttpResponse(content_type="text/csv")
        cd = f'attachment; filename="{self.get_csv_filename()}"'
        response["Content-Disposition"] = cd
        # Add BOM for Excel compatibility
        response.write("\ufeff")

        self.write_csv(response)
        return response


def health_check(request):
    """Unauthenticated status endpoint (LB/uptime-monitor friendly) - reports ok/warning/
    critical per component, never raw numbers (see backend's superadmin-only dashboard
    for that). 200 unless something is actually critical, so a single "disk getting
    full" warning doesn't pull the box out of a load balancer's rotation."""
    results = run_checks()
    overall = overall_level(results)
    body = {"status": overall, "checks": {name: r["level"] for name, r in results.items()}}
    return JsonResponse(body, status=503 if overall == CRITICAL else 200)


# noinspection PyUnusedLocal
def not_found(request, exception=None):
    response = render(request, "404.html", {})
    response.status_code = 404
    return response


# noinspection PyUnusedLocal
def server_error(request, exception=None):
    response = render(request, "500.html", {})
    response.status_code = 500
    return response


@allowed_user_required
def impersonate(request, uid):
    """
    Override django-impersonate view to handle users who have uuids as pk.
    Takes in the UID of the user to impersonate.
    Takes in the UID of the user to impersonate.
    Takes in the UID of the user to impersonate.
    View will fetch the User instance and store it
    in the request.session under the '_impersonate' key.

    The middleware will then pick up on it and adjust the
    request object as needed.

    Also store the user's 'starting'/'original' URL so
    we can return them to it.
    """
    try:
        new_user = get_object_or_404(FamilyUser, pk=uid)
    except ValueError:
        # Invalid uid value passed
        raise Http404("Invalid value given.")
    if check_allow_for_user(request, new_user):
        request.session["_impersonate"] = str(new_user.pk)
        request.session["_impersonate_start"] = datetime.now(tz=timezone.utc).timestamp()
        prev_path = request.headers.get("referer")
        if prev_path:
            request.session["_impersonate_prev_path"] = request.build_absolute_uri(prev_path)

        request.session.modified = True  # Let's make sure...
        # can be used to hook up auditing of the session
        session_begin.send(
            sender=None,
            impersonator=request.user,
            impersonating=new_user,
            request=request,
        )
    return redirect(get_redir_path(request))
