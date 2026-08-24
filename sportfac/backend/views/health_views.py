from django.views.generic import TemplateView

from sportfac.health import overall_level
from sportfac.health import run_checks

from .mixins import SuperuserRequiredMixin


class ServerHealthView(SuperuserRequiredMixin, TemplateView):
    """Superuser-only detail view for the public /_health-kc/ status endpoint - same
    checks, but with the raw numbers (disk/RAM/load) that endpoint deliberately omits."""

    template_name = "backend/health.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        results = run_checks()
        context["results"] = results
        context["overall"] = overall_level(results)
        return context
