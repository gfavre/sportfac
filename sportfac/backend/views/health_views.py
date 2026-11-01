from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from sportfac.health import overall_level
from sportfac.health import run_checks
from sportfac.service_health import run_service_checks

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
    "postfinance": "PostFinance",
    "datatrans": "Datatrans",
    "email": _("Email"),
    "sso": "SSO",
    "phantomjs": "PhantomJsCloud (PDF)",
    "recaptcha": "reCAPTCHA",
    "sentry": "Sentry",
}

LEVEL_LABELS = {
    "ok": _("OK"),
    "warning": _("Warning"),
    "critical": _("Critical"),
    "disabled": _("Not enabled"),
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
    "http_status": _("HTTP status"),
    "duration_ms": _("Duration (ms)"),
}

# Unlike free_gb/total_gb/available_mb/total_mb (whose label already spells out the
# unit), free_percent's label ("Free space") doesn't - "69.3" alone reads as a mystery
# number rather than a percentage.
DETAIL_UNITS = {"free_percent": "%"}

# Keys large enough to benefit from a thousands separator (available_mb/total_mb in
# particular: RAM in MB on any real box is a 5-6 digit number).
DETAIL_THOUSANDS_KEYS = {"available_mb", "total_mb", "free_gb", "total_gb", "queue_length"}

# Short, plain-language explanations for the two checks people most often misread at a
# glance - shown as a note under that row rather than crammed into a label.
CHECK_EXPLANATIONS = {
    "load": _(
        "Load average (1/5/15 min): how many processes wanted a CPU core, averaged over "
        "that window. A value up to the CPU count means every core is busy but nothing is "
        "queueing yet - still healthy. Only past the CPU count do processes actually wait."
    ),
    "memory": _(
        "Available memory: what the system could hand out right now, including memory "
        "held by cache/buffers that the kernel would reclaim if something needed it - not "
        "just literally-unused RAM, which is usually a much smaller and misleading number."
    ),
}


def _swiss_number(value):
    """1000 -> "1'000", 460.4 -> "460.4" - Swiss-style thousands separator, keeping a
    float's existing precision (health.py already rounds free_gb/total_gb to 1 decimal;
    formatting those as integers would silently drop it). Falls back to the plain value
    for anything that isn't actually numeric (e.g. an error string)."""
    if isinstance(value, int):
        return f"{value:,}".replace(",", "'")
    if isinstance(value, float):
        return f"{value:,.1f}".replace(",", "'")
    return value


def _check_label(name):
    if name.startswith("database:"):
        return f"{_('Database')} : {name.partition(':')[2]}"
    if name.startswith("cache:"):
        return f"{_('Cache')} : {name.partition(':')[2]}"
    return CHECK_LABELS.get(name, name)


@method_decorator(never_cache, name="dispatch")
class ServerHealthView(SuperuserRequiredMixin, TemplateView):
    """Superuser-only infrastructure and external service diagnostics."""

    template_name = "backend/health.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_results = run_checks()
        raw_results.update(run_service_checks())
        context["checked_at"] = timezone.now()
        context["schema_name"] = getattr(self.request.tenant, "schema_name", "public")
        context["results"] = [
            {
                "name": name,
                "label": _check_label(name),
                "level": result["level"],
                "level_label": LEVEL_LABELS.get(result["level"], result["level"]),
                "explanation": CHECK_EXPLANATIONS.get(name),
                "detail": [
                    {
                        "label": DETAIL_LABELS.get(key, key),
                        "value": (
                            f"{_swiss_number(value) if key in DETAIL_THOUSANDS_KEYS else value}"
                            f"{DETAIL_UNITS.get(key, '')}"
                        ),
                    }
                    for key, value in result["detail"].items()
                ],
            }
            for name, result in raw_results.items()
        ]
        overall = overall_level(raw_results)
        context["overall"] = overall
        context["overall_label"] = LEVEL_LABELS.get(overall, overall)
        return context
