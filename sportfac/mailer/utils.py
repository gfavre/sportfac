from django.template.loader import render_to_string
from django_tenants.utils import tenant_context

from sportfac.context_processors import kepchup_context


def render_email_content(template_name, extra_context=None, tenant=None):
    """Render an email template outside of an HTTP request (typically from a Celery task).

    render_to_string() only runs Django's template context processors when given a
    request, which background tasks never have - so kepchup_context (the KEPCHUP_*
    settings every other page gets for free) is merged in here by hand instead,
    same as registrations/pdf.py already does for PDF rendering.

    `tenant`, if given, switches to that tenant's schema for the render; otherwise
    whatever tenant is already active on the current DB connection is used as-is.
    """
    context = kepchup_context(None)
    if extra_context:
        context.update(extra_context)
    if tenant is not None:
        with tenant_context(tenant):
            return render_to_string(template_name, context=context)
    return render_to_string(template_name, context=context)
