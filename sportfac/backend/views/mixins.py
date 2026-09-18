from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlsplit

from braces.views import LoginRequiredMixin
from braces.views import UserPassesTestMixin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.text import slugify


LIST_RETURN_NAMES = (
    "activity-list",
    "course-list",
    "roles-list",
    "registration-list",
    "bill-list",
    "transport-list",
    "user-list",
    "instructor-list",
    "manager-list",
    "restricted-admin-list",
    "teacher-list",
    "child-list",
)
LIST_STATE_PARAMETERS = {
    "q",
    "order",
    "page",
    "length",
    "panes",
    "only_js",
    "date_from",
    "date_to",
    "status",
    "amount",
    "start",
    "end",
}


class ListReturnMixin:
    """Opt-in return to a filtered backend list, without accepting arbitrary redirects."""

    def get_list_return_url(self):
        value = self.request.GET.get("list_return", "")
        if not value or any(ord(char) < 32 for char in value):
            return None
        try:
            target = urlsplit(value)
        except ValueError:
            return None
        paths = {reverse(f"backend:{name}") for name in LIST_RETURN_NAMES}
        if target.scheme or target.netloc or target.path not in paths or value.startswith("//"):
            return None
        query = urlencode([(key, val) for key, val in parse_qsl(target.query) if key in LIST_STATE_PARAMETERS])
        return target.path + (f"?{query}" if query else "")

    def get_success_url(self):
        return self.get_list_return_url() or super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["list_return_url"] = self.get_list_return_url()
        context["list_return_paths"] = [reverse(f"backend:{name}") for name in LIST_RETURN_NAMES]
        return context


class BackendMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports manager"""

    def test_func(self, user):
        return user.is_active and (user.is_staff or user.is_superuser or user.is_manager or user.is_restricted_manager)


class FullBackendMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports manager or course supervisor."""

    def test_func(self, user):
        return user.is_active and (user.is_staff or user.is_superuser or user.is_manager)


class KepchupStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports manager or course supervisor."""

    def test_func(self, user):
        return user.is_active and user.is_kepchup_staff


class SuperuserRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a superuser."""

    def test_func(self, user):
        return user.is_active and user.is_superuser


class ExcelResponseMixin:
    filename = "download"
    resource_class = None

    def get_resource_class(self):
        assert self.resource_class is not None, (
            "'%s' should either include a `resource_class` attribute, "
            "or override the `get_resource_class()` method." % self.__class__.__name__
        )

        return self.resource_class

    def get_resource(self):
        return self.get_resource_class()()

    def get_filename(self):
        return self.filename

    def render_to_response(self, **response_kwargs):
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="%s.xlsx"' % slugify(self.get_filename())
        resource = self.get_resource()
        try:
            # noinspection PyUnresolvedReferences
            export = resource.export(queryset=self.get_queryset())
        except AttributeError:
            export = resource.export()
        response.write(export.xlsx)
        return response

    def get(self, request, *args, **kwargs):
        return self.render_to_response()
