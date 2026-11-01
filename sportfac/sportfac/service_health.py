"""Private service diagnostics. Never call these from the public uptime probe.

Only read APIs are used: no payment, email, PDF rendering or Sentry event is created.
Provider responses and exception strings may contain credentials or personal data;
return only fixed messages and numeric HTTP statuses.
"""
import socket
import ssl
from time import monotonic
from urllib.parse import urlsplit
from urllib.parse import urlunsplit
from uuid import uuid4

import requests
from django.conf import settings
from django.core.cache import caches
from django.core.mail import get_connection
from django.db import connections
from django.utils.translation import gettext_lazy as _
from postfinancecheckout import Configuration
from postfinancecheckout.api import TransactionServiceApi

from .health import CRITICAL
from .health import OK
from .health import WARNING


TIMEOUT = 3
DISABLED = "disabled"
AUTHENTICATED = {"note": _("Authenticated API access verified. No operation was created.")}
MISSING = {"note": _("Required credentials are missing. Check the service configuration.")}
NETWORK_ONLY = _("HTTPS access verified only. Credentials and the complete workflow were not tested.")


def _http_check(url, authenticated=False, **kwargs):
    # Do not follow redirects with credentials; never include response bodies in diagnostics.
    with requests.get(url, timeout=TIMEOUT, allow_redirects=False, stream=True, **kwargs) as response:
        if response.status_code != 200 and (authenticated or response.status_code not in (301, 302, 303, 307, 308)):
            return CRITICAL, {"http_status": response.status_code}
    return (OK, AUTHENTICATED) if authenticated else (WARNING, {"note": NETWORK_ONLY})


def _check_postfinance():
    if settings.KEPCHUP_NO_PAYMENT or settings.KEPCHUP_PAYMENT_METHOD != "postfinance":
        return DISABLED, {}
    if not all((settings.POSTFINANCE_USER_ID, settings.POSTFINANCE_API_SECRET, settings.POSTFINANCE_SPACE_ID)):
        return CRITICAL, MISSING
    config = Configuration(
        user_id=settings.POSTFINANCE_USER_ID,
        api_secret=settings.POSTFINANCE_API_SECRET,
        request_timeout=TIMEOUT,
    )
    # Count is a read operation, works with an empty space and returns no customer data.
    TransactionServiceApi(config).count(space_id=settings.POSTFINANCE_SPACE_ID)
    return OK, AUTHENTICATED


def _check_datatrans():
    if settings.KEPCHUP_NO_PAYMENT or settings.KEPCHUP_PAYMENT_METHOD != "datatrans":
        return DISABLED, {}
    if not all((settings.DATATRANS_USER, settings.DATATRANS_PASSWORD)):
        return CRITICAL, MISSING
    from payments.models import DatatransTransaction

    # ORM uses the request's selected period. Never switch to another period to find a payment.
    transaction_id = DatatransTransaction.objects.order_by("-pk").values_list("transaction_id", flat=True).first()
    if not transaction_id:
        return WARNING, {"note": _("No existing transaction in this period: API access could not be verified.")}
    api_url = settings.DATATRANS_API_URL
    base = api_url.geturl() if hasattr(api_url, "geturl") else api_url
    return _http_check(
        f"{base.rstrip('/')}/v1/transactions/{transaction_id}",
        authenticated=True,
        auth=(settings.DATATRANS_USER, settings.DATATRANS_PASSWORD),
    )


def _check_email():
    backend = settings.EMAIL_BACKEND
    if backend == "anymail.backends.postmark.EmailBackend":
        token = getattr(settings, "ANYMAIL", {}).get("POSTMARK_SERVER_TOKEN")
        if not token:
            return CRITICAL, MISSING
        return _http_check(
            "https://api.postmarkapp.com/server",
            authenticated=True,
            headers={"Accept": "application/json", "X-Postmark-Server-Token": token},
        )
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        with get_connection(timeout=TIMEOUT) as connection:
            if connection.connection is None:
                return CRITICAL, {"note": _("The SMTP connection could not be opened.")}
        return OK, {"note": _("SMTP connection verified. No email was sent.")}
    return WARNING, {"note": _("This email backend has no automatic connection check.")}


def _check_sso():
    if not settings.KEPCHUP_USE_SSO:
        return DISABLED, {}
    if not all((settings.SSO_SERVER, settings.SSO_PUBLIC_KEY, settings.SSO_PRIVATE_KEY)):
        return CRITICAL, MISSING
    # Creating an SSO request token would mutate the remote session store.
    parts = urlsplit(settings.SSO_SERVER)
    origin = urlunsplit((parts.scheme, parts.netloc, "/", "", ""))
    return _http_check(origin)


def _check_phantomjs():
    if not settings.PHANTOMJSCLOUD_APIKEY:
        return DISABLED, {}
    # Rendering a document consumes credits. Test public HTTPS access instead.
    return _http_check("https://phantomjscloud.com/")


def _check_recaptcha():
    if not getattr(settings, "RECAPTCHA_PUBLIC_KEY", ""):
        return DISABLED, {}
    if not getattr(settings, "RECAPTCHA_PRIVATE_KEY", ""):
        return CRITICAL, MISSING
    # siteverify requires a real browser challenge token; an empty token cannot validate the key.
    return _http_check("https://www.google.com/recaptcha/api.js")


def _check_sentry():
    dsn = getattr(settings, "SENTRY_DSN", "")
    if not dsn:
        return DISABLED, {}
    parts = urlsplit(dsn)
    # Strip DSN credentials. Sending a test event would create an actual incident.
    with socket.create_connection((parts.hostname, parts.port or 443), timeout=TIMEOUT) as connection:
        with ssl.create_default_context().wrap_socket(connection, server_hostname=parts.hostname):
            pass
    return WARNING, {"note": _("TLS connection verified only. Sentry event delivery was not tested.")}


def _database_check(alias):
    with connections[alias].cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return OK, {}


def _cache_check(alias):
    cache = caches[alias]
    key = f"healthcheck-{uuid4().hex}"
    try:
        cache.set(key, "1", timeout=10)
        return (OK if cache.get(key) == "1" else CRITICAL), {}
    finally:
        cache.delete(key)


SERVICE_CHECKS = {
    "postfinance": _check_postfinance,
    "datatrans": _check_datatrans,
    "email": _check_email,
    "sso": _check_sso,
    "phantomjs": _check_phantomjs,
    "recaptcha": _check_recaptcha,
    "sentry": _check_sentry,
}


def _run_check(check, *args):
    start = monotonic()
    try:
        level, detail = check(*args)
    except Exception as exc:  # noqa: BLE001 - failures must not hide the remaining checks
        detail = {"error": _("Connection failed. Check credentials, network access and service availability.")}
        status = getattr(exc, "status", None)
        if isinstance(status, int):
            detail["http_status"] = status
        level = CRITICAL
    return {"level": level, "detail": {**detail, "duration_ms": round((monotonic() - start) * 1000)}}


def run_service_checks():
    results = {}
    # The existing infrastructure checks cover default DB/cache; include secondary aliases,
    # notably the shared Montreux user database and the separate session cache.
    for alias in connections:
        if alias != "default":
            results[f"database:{alias}"] = _run_check(_database_check, alias)
    for alias in settings.CACHES:
        if alias != "default":
            results[f"cache:{alias}"] = _run_check(_cache_check, alias)
    for name, check in SERVICE_CHECKS.items():
        results[name] = _run_check(check)
    return results
