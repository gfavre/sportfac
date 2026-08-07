import datetime
import logging

from django.core.cache import cache
from django.http import FileResponse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.cache import never_cache

from backend.dynamic_preferences_registry import global_preferences_registry


logger = logging.getLogger(__name__)


class BillMixin:
    def get_context_data(self, **kwargs):
        # noinspection PyUnresolvedReferences
        context = super().get_context_data(**kwargs)
        preferences = global_preferences_registry.manager()
        offset_days = preferences["payment__DELAY_DAYS"]
        # noinspection PyUnresolvedReferences
        if hasattr(self, "object"):
            base_date = self.object.created  # self.request.REGISTRATION_END
        else:
            base_date = now()
        context["delay"] = base_date + datetime.timedelta(days=offset_days)
        context["iban"] = preferences["payment__IBAN"]
        context["address"] = preferences["payment__ADDRESS"]
        context["place"] = preferences["payment__PLACE"]
        context["display_qr_invoice"] = preferences["payment__DISPLAY_QR_INVOICE"]

        return context


@method_decorator(never_cache, name="dispatch")
class PaymentMixin:
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)  # noqa


class BillPdfDownloadMixin:
    """Serves a bill's PDF, generating it asynchronously (via Celery) on first request.

    GET returns either the PDF itself (once generated) or a small JSON "pending"
    payload with HTTP 202 while generation is in progress, matched by the polling
    client in registrations/pdf-download-button.html. A short cache lock keeps
    repeated polls from each queueing their own (expensive, Playwright-driven)
    generation task while one is already running.

    Subclasses must implement get_queryset() to scope which bills the requesting
    user may fetch (see registrations.views.user.BillDetailView and
    backend.views.registration_views.BillDetailView for the equivalent pattern).
    """

    def get_queryset(self):
        raise NotImplementedError

    def get(self, request, pk, *args, **kwargs):
        bill = get_object_or_404(self.get_queryset(), pk=pk)
        bill.refresh_from_db(fields=["pdf"])
        if bill.pdf:
            response = FileResponse(bill.pdf.open("rb"), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="facture-{bill.billing_identifier}.pdf"'
            return response

        lock_key = f"bill-pdf-generating-{bill.pk}"
        if cache.add(lock_key, True, timeout=60):
            from ..tasks import generate_invoice_pdf

            generate_invoice_pdf.delay(bill_id=bill.pk)
        return JsonResponse({"status": "pending"}, status=202)
