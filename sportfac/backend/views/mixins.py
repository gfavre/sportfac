from django.http import HttpResponse
from django.utils.text import slugify

from braces.views import GroupRequiredMixin, LoginRequiredMixin

from backend import MANAGERS_GROUP



class BackendMixin(GroupRequiredMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a member 
       of sports managers group."""
    group_required = MANAGERS_GROUP


class ExcelResponseMixin(object):
    filename = 'download'
    resource_class = None

    def get_resource_class(self):
        assert self.resource_class is not None, (
            "'%s' should either include a `resource_class` attribute, "
            "or override the `get_resource_class()` method."
            % self.__class__.__name__
        )

        return self.resource_class

    def get_resource(self):
        return self.get_resource_class()()

    def get_filename(self):
        return self.filename

    def render_to_response(self, **response_kwargs):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % slugify(self.get_filename())
        resource = self.get_resource()
        try:
            export = resource.export(queryset=self.get_queryset())
        except AttributeError:
            export = resource.export()
        response.write(export.xlsx)
        return response

    def get(self, request, *args, **kwargs):
        return self.render_to_response()