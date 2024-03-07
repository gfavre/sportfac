from django.http import HttpResponse
from django.utils.text import slugify

from braces.views import LoginRequiredMixin, UserPassesTestMixin


class BackendMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports manager"""

    def test_func(self, user):
        return user.is_active and (user.is_staff or user.is_superuser or user.is_manager or user.is_restricted_manager)


class KepchupStaffMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports manager or course supervisor."""

    def test_func(self, user):
        return user.is_active and user.is_kepchup_staff


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
