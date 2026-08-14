from unittest.mock import patch

from django.test import override_settings

from sportfac.utils import TenantTestCase

from ..utils import render_email_content


class RenderEmailContentTests(TenantTestCase):
    @override_settings(KEPCHUP_PAYMENT_METHOD="iban")
    @patch("mailer.utils.render_to_string")
    def test_includes_kepchup_context_without_a_request(self, mock_render):
        # Regression test: render_to_string() only runs template context processors
        # when given a request, which background tasks (the only callers of this
        # helper) never have - PAYMENT_METHOD (and the rest of kepchup_context) must
        # still be present.
        render_email_content("some/template.txt")
        context = mock_render.call_args.kwargs["context"]
        self.assertEqual(context["PAYMENT_METHOD"], "iban")

    @patch("mailer.utils.render_to_string")
    def test_extra_context_is_merged_in(self, mock_render):
        render_email_content("some/template.txt", extra_context={"bill": "some-bill"})
        context = mock_render.call_args.kwargs["context"]
        self.assertEqual(context["bill"], "some-bill")

    @patch("mailer.utils.render_to_string")
    def test_extra_context_overrides_kepchup_context_on_key_collision(self, mock_render):
        render_email_content("some/template.txt", extra_context={"PAYMENT_METHOD": "custom"})
        context = mock_render.call_args.kwargs["context"]
        self.assertEqual(context["PAYMENT_METHOD"], "custom")

    @patch("mailer.utils.tenant_context")
    @patch("mailer.utils.render_to_string")
    def test_switches_to_the_given_tenant(self, _mock_render, mock_tenant_context):
        render_email_content("some/template.txt", tenant=self.tenant)
        mock_tenant_context.assert_called_once_with(self.tenant)

    @patch("mailer.utils.tenant_context")
    @patch("mailer.utils.render_to_string")
    def test_uses_current_tenant_when_none_given(self, _mock_render, mock_tenant_context):
        render_email_content("some/template.txt")
        mock_tenant_context.assert_not_called()
