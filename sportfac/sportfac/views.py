from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, reverse
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