from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import RequestContext
from django.views.generic.base import RedirectView

from braces.views import LoginRequiredMixin

from .context_processors import wizard_context


class OpenedPeriodMixin(object):
    "Raise a 403 status when period is not opened"
    
    def dispatch(self, request, *args, **kwargs):
        "Called before get or post methods"
        if request.REGISTRATION_OPENED:
            return super(OpenedPeriodMixin, self).dispatch(request, *args, **kwargs)
        raise PermissionDenied


class PhaseForbiddenMixin(LoginRequiredMixin):
    forbidden_phases = None
    
    def get_forbidden_phases(self):
        if self.forbidden_phases is None:
            raise ImproperlyConfigured(
                '{0} requires the "forbidden_phases" attribute to be '
                'set.'.format(self.__class__.__name__))
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
            return redirect_to_login(request.get_full_path(),
                                 self.get_login_url(),
                                 self.get_redirect_field_name())
        return super(PhaseForbiddenMixin, self).dispatch(request, *args, **kwargs)


class WizardMixin(OpenedPeriodMixin):
    
    def get(self, request, *args, **kwargs):
        "If wizard is finished, go straight to last page."
        context = wizard_context(request)
        if not context['current_step'].activable:
            return redirect(context['max_step'])
        #if request.user.finished_registration:
        #    end_url = reverse('wizard_billing')
        #    if not request.path == end_url:
        #        return redirect(end_url)
        return super(WizardMixin, self).get(request, *args, **kwargs)


class WizardView(WizardMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        context = wizard_context(self.request)
        return context.get('max_step')


class CSVMixin(object):
    def get_csv_filename(self):
        return NotImplementedError
    
    def write_csv(self, filelike):
        return NotImplementedError
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        response = HttpResponse(content_type='text/csv')
        cd = u'attachment; filename="{0}"'.format(self.get_csv_filename())
        response['Content-Disposition'] = cd
        self.write_csv(response)
        return response
