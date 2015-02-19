from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic.base import RedirectView
from django.template import RequestContext

class OpenedPeriodMixin(object):
    "Raise a 403 status when period is not opened"
    
    def dispatch(self, request, *args, **kwargs):
        "Called before get or post methods"
        if request.REGISTRATION_OPENED:
            return super(OpenedPeriodMixin, self).dispatch(request, *args, **kwargs)
        raise PermissionDenied

class WizardMixin(OpenedPeriodMixin):
    
    def get(self, request, *args, **kwargs):
        "If wizard is finished, go straight to last page."
        context = RequestContext(self.request)
        if not context['current_step'].activable:
            return redirect(context['max_step'])
        #if request.user.finished_registration:
        #    end_url = reverse('wizard_billing')
        #    if not request.path == end_url:
        #        return redirect(end_url)
        return super(WizardMixin, self).get(request, *args, **kwargs)

class WizardView(WizardMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        context = RequestContext(self.request)
        return context.get('max_step')


class CSVMixin(object):
    def get_csv_filename(self):
        return NotImplementedError
    
    def write_csv(self, filelike):
        return NotImplementedError
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = HttpResponse(content_type='text/csv')
        cd = 'attachment; filename="{0}"'.format(self.get_csv_filename())
        response['Content-Disposition'] = cd
        self.write_csv(response)
        return response
