from unittest.mock import MagicMock
from unittest.mock import patch

import requests
from django.test import SimpleTestCase
from django.test import override_settings
from postfinancecheckout.rest import ApiException

from sportfac import service_health
from sportfac.health import CRITICAL
from sportfac.health import OK
from sportfac.health import WARNING


class ServiceHealthTests(SimpleTestCase):
    @override_settings(SENTRY_DSN="https://public:private@ingest.example.com/123")
    @patch("sportfac.service_health.ssl.create_default_context")
    @patch("sportfac.service_health.socket.create_connection")
    def test_sentry_checks_tls_without_sending_event_or_credentials(self, connect, context):
        self.assertEqual(service_health._check_sentry()[0], WARNING)
        connect.assert_called_once_with(("ingest.example.com", 443), timeout=3)
        context.return_value.wrap_socket.assert_called_once_with(
            connect.return_value.__enter__.return_value, server_hostname="ingest.example.com"
        )

    @override_settings(PHANTOMJSCLOUD_APIKEY="secret", RECAPTCHA_PUBLIC_KEY="public", RECAPTCHA_PRIVATE_KEY="secret")
    @patch("sportfac.service_health._http_check", return_value=(WARNING, {}))
    def test_pdf_and_recaptcha_only_test_public_connectivity(self, http):
        self.assertEqual(service_health._check_phantomjs()[0], WARNING)
        http.assert_called_with("https://phantomjscloud.com/")
        self.assertEqual(service_health._check_recaptcha()[0], WARNING)
        http.assert_called_with("https://www.google.com/recaptcha/api.js")

    @override_settings(
        KEPCHUP_NO_PAYMENT=False,
        KEPCHUP_PAYMENT_METHOD="postfinance",
        POSTFINANCE_USER_ID=123,
        POSTFINANCE_SPACE_ID=456,
        POSTFINANCE_API_SECRET="private-secret",
    )
    @patch("sportfac.service_health.TransactionServiceApi")
    @patch("sportfac.service_health.Configuration")
    def test_postfinance_authentication_without_creating_a_payment(self, configuration, service):
        service.return_value.count.return_value = 0
        level, _ = service_health._check_postfinance()
        self.assertEqual(level, OK)
        configuration.assert_called_once_with(user_id=123, api_secret="private-secret", request_timeout=3)
        service.return_value.count.assert_called_once_with(space_id=456)
        service.return_value.create.assert_not_called()

    @override_settings(KEPCHUP_NO_PAYMENT=True)
    @patch("sportfac.service_health.TransactionServiceApi")
    def test_disabled_payment_does_not_contact_provider(self, service):
        self.assertEqual(service_health._check_postfinance()[0], service_health.DISABLED)
        self.assertEqual(service_health._check_datatrans()[0], service_health.DISABLED)
        service.assert_not_called()

    @override_settings(KEPCHUP_NO_PAYMENT=False, KEPCHUP_PAYMENT_METHOD="postfinance", POSTFINANCE_API_SECRET="")
    @patch("sportfac.service_health.TransactionServiceApi")
    def test_missing_payment_credentials_are_critical(self, service):
        self.assertEqual(service_health._check_postfinance()[0], CRITICAL)
        service.assert_not_called()

    @patch("sportfac.service_health.requests.get")
    def test_postmark_uses_authenticated_read_api(self, get):
        get.return_value.__enter__.return_value.status_code = 200
        with override_settings(
            EMAIL_BACKEND="anymail.backends.postmark.EmailBackend", ANYMAIL={"POSTMARK_SERVER_TOKEN": "secret"}
        ):
            self.assertEqual(service_health._check_email()[0], OK)
        get.assert_called_once_with(
            "https://api.postmarkapp.com/server",
            timeout=3,
            stream=True,
            allow_redirects=False,
            headers={"Accept": "application/json", "X-Postmark-Server-Token": "secret"},
        )

    @patch("sportfac.service_health.requests.get")
    def test_http_failure_reports_only_status_and_closes_response(self, get):
        response = get.return_value.__enter__.return_value
        response.status_code = 401
        response.text = "secret-token and customer@example.com"
        level, detail = service_health._http_check("https://example.com", authenticated=True)
        self.assertEqual(level, CRITICAL)
        self.assertEqual(detail, {"http_status": 401})
        get.return_value.__exit__.assert_called_once()

    @patch("sportfac.service_health.requests.get")
    def test_redirect_never_verifies_authentication(self, get):
        get.return_value.__enter__.return_value.status_code = 302
        self.assertEqual(service_health._http_check("https://example.com", authenticated=True)[0], CRITICAL)
        self.assertEqual(service_health._http_check("https://example.com")[0], WARNING)

    def test_timeouts_and_provider_errors_are_sanitized_and_do_not_stop_other_checks(self):
        for error in (requests.Timeout("secret"), ApiException(status=403, reason="private-secret")):
            with self.subTest(error=type(error).__name__):
                failing = MagicMock(side_effect=error)
                succeeding = MagicMock(return_value=(OK, {}))
                with patch.object(service_health, "SERVICE_CHECKS", {"failed": failing, "next": succeeding}):
                    result = service_health.run_service_checks()
                self.assertEqual(result["failed"]["level"], CRITICAL)
                self.assertNotIn("secret", str(result))
                self.assertEqual(result["next"]["level"], OK)
                succeeding.assert_called_once()

    @override_settings(
        KEPCHUP_USE_SSO=True, SSO_SERVER="https://users.example.com/server/", SSO_PUBLIC_KEY="a", SSO_PRIVATE_KEY="b"
    )
    @patch("sportfac.service_health._http_check", return_value=(WARNING, {}))
    def test_sso_check_does_not_request_tokens(self, http):
        self.assertEqual(service_health._check_sso()[0], WARNING)
        http.assert_called_once_with("https://users.example.com/")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend")
    @patch("sportfac.service_health.get_connection")
    def test_smtp_connection_closes_without_sending_email(self, get_connection):
        self.assertEqual(service_health._check_email()[0], OK)
        get_connection.assert_called_once_with(timeout=3)
        get_connection.return_value.__exit__.assert_called_once()
        get_connection.return_value.send_messages.assert_not_called()

    @override_settings(
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
            "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "health-tests"},
        }
    )
    @patch.object(service_health, "SERVICE_CHECKS", {})
    def test_secondary_cache_round_trip_and_cleanup(self):
        self.assertEqual(service_health.run_service_checks()["cache:sessions"]["level"], OK)
        cache = MagicMock()
        cache.get.return_value = None
        with patch("sportfac.service_health.caches", {"sessions": cache}):
            self.assertEqual(service_health._cache_check("sessions")[0], CRITICAL)
        key = cache.set.call_args[0][0]
        cache.delete.assert_called_once_with(key)

    @patch("sportfac.service_health.connections")
    @patch.object(service_health, "SERVICE_CHECKS", {})
    def test_secondary_database_is_checked_without_switching_tenants(self, connections):
        connections.__iter__.return_value = iter(("default", "master_users"))
        results = service_health.run_service_checks()
        self.assertEqual(results["database:master_users"]["level"], OK)
        connections["master_users"].cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
            "SELECT 1"
        )

    @patch("sportfac.service_health.requests.get")
    @override_settings(
        KEPCHUP_NO_PAYMENT=False,
        KEPCHUP_PAYMENT_METHOD="datatrans",
        DATATRANS_USER="user",
        DATATRANS_PASSWORD="secret",
    )
    def test_datatrans_reads_existing_transaction_in_current_period(self, get):
        get.return_value.__enter__.return_value.status_code = 200
        with patch("payments.models.DatatransTransaction.objects") as manager:
            manager.order_by.return_value.values_list.return_value.first.return_value = "1234567890"
            self.assertEqual(service_health._check_datatrans()[0], OK)
            self.assertTrue(get.call_args[0][0].endswith("/v1/transactions/1234567890"))
            self.assertEqual(get.call_args[1]["auth"], ("user", "secret"))
            manager.create.assert_not_called()
            manager.order_by.return_value.values_list.return_value.first.return_value = None
            get.reset_mock()
            self.assertEqual(service_health._check_datatrans()[0], WARNING)
            get.assert_not_called()
