import datetime
import logging

from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.cache import never_cache

import requests
from postfinancecheckout.rest import ApiException
from sentry_sdk import capture_exception

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

        return context


@method_decorator(never_cache, name="dispatch")
class PaymentMixin:
    def get_transaction(self, invoice):
        if settings.KEPCHUP_PAYMENT_METHOD == "datatrans":
            from payments.datatrans import get_transaction

            try:
                transaction = get_transaction(self.request, invoice)  # noqa
            except requests.exceptions.RequestException:
                transaction = None
            return transaction

        if settings.KEPCHUP_PAYMENT_METHOD == "postfinance":
            from payments.postfinance import get_transaction

            try:
                transaction = get_transaction(self.request, invoice)  # noqa
            except requests.exceptions.RequestException:
                transaction = None
            except ApiException as exc:
                capture_exception(exc)
                logger.error("Postfinance API error: %s", exc)
                transaction = None
            return transaction
        return None

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)  # noqa
