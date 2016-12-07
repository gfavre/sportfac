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

    def get_resource(self):
        raise NotImplementedError

    def get_filename(self):
        return self.filename

    def render_to_response(self, **response_kwargs):
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="%s.xlsx"' % slugify(self.get_filename())
        resource = self.get_resource()
        response.write(resource.export().xlsx)
        return response

