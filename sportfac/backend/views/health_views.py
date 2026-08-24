from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from sportfac.health import overall_level
from sportfac.health import run_checks

from .mixins import SuperuserRequiredMixin


# Display-only labels for the superadmin dashboard - the raw identifiers (database, ok,
# free_percent, ...) stay untranslated everywhere else: they're the public /_health-kc/
# endpoint's stable, machine-readable contract, not user-facing text.
CHECK_LABELS = {
    "database": _("Database"),
    "cache": _("Cache"),
    "broker": _("Message broker"),
    "disk": _("Disk"),
    "memory": _("Memory"),
    "load": _("Load"),
}

LEVEL_LABELS = {
    "ok": _("OK"),
    "warning": _("Warning"),
    "critical": _("Critical"),
}

DETAIL_LABELS = {
    "error": _("Error"),
    "note": _("Note"),
    "free_percent": _("Free space"),
    "free_gb": _("Free (GB)"),
    "total_gb": _("Total (GB)"),
    "available_mb": _("Available (MB)"),
    "total_mb": _("Total (MB)"),
    "queue": _("Queue name"),
    "queue_length": _("Queue length"),
    "queue_length_error": _("Queue length error"),
    "load1": _("Load (1 min)"),
    "load5": _("Load (5 min)"),
    "load15": _("Load (15 min)"),
    "cpu_count": _("CPU count"),
}


class ServerHealthView(SuperuserRequiredMixin, TemplateView):
    """Superuser-only detail view for the public /_health-kc/ status endpoint - same
    checks, but with the raw numbers (disk/RAM/load/queue length) that endpoint
    deliberately omits."""

    template_name = "backend/health.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_results = run_checks()
        context["results"] = [
            {
                "name": name,
                "label": CHECK_LABELS.get(name, name),
                "level": result["level"],
                "level_label": LEVEL_LABELS.get(result["level"], result["level"]),
                "detail": [
                    {"label": DETAIL_LABELS.get(key, key), "value": value} for key, value in result["detail"].items()
                ],
            }
            for name, result in raw_results.items()
        ]
        overall = overall_level(raw_results)
        context["overall"] = overall
        context["overall_label"] = LEVEL_LABELS.get(overall, overall)
        return context
