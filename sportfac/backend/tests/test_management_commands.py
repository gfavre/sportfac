"""Tests for `manage.py check_deployment` (backend/management/commands/check_deployment.py) -
a manual, post-install sanity check that a tenant instance's static configuration (theme
directories, collected static files, referenced instructor-email documents) is actually
in place, rather than discovering that the hard way when mailer.tasks.send_instructors_email
refuses to send an email over a single missing file.
"""
import os
import tempfile
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.test import override_settings

from sportfac.utils import TenantTestCase


def _run(**kwargs):
    out = StringIO()
    exit_code = 0
    try:
        call_command("check_deployment", stdout=out, **kwargs)
    except SystemExit as exc:
        exit_code = exc.code
    return exit_code, out.getvalue()


class CheckDeploymentCommandTest(TenantTestCase):
    def test_passes_against_the_real_local_settings(self):
        # local.py's theme dirs, collected static, and configured instructor documents
        # are all genuinely present in this dev checkout - this is the "nothing's wrong"
        # baseline the failure-injecting tests below are compared against.
        exit_code, output = _run()
        self.assertEqual(exit_code, 0)
        self.assertIn("All checks passed.", output)
        self.assertNotIn("FAIL", output)

    def test_fails_on_a_missing_instructor_email_document(self):
        with override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/does-not-exist.pdf"]):
            exit_code, output = _run()
        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL", output)
        self.assertIn("does-not-exist.pdf", output)

    def test_fails_on_a_missing_theme_static_dir(self):
        missing_dir = os.path.join(tempfile.gettempdir(), "definitely-not-a-real-theme-dir")
        with override_settings(STATICFILES_DIRS=[missing_dir]):
            exit_code, output = _run()
        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL", output)
        self.assertIn(missing_dir, output)

    def test_fails_on_a_missing_static_root(self):
        missing_dir = os.path.join(tempfile.gettempdir(), "definitely-not-a-collected-static-root")
        with override_settings(STATIC_ROOT=missing_dir):
            exit_code, output = _run()
        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL", output)
        self.assertIn("collectstatic", output)

    def test_fails_on_an_empty_static_root(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            with override_settings(STATIC_ROOT=empty_dir):
                exit_code, output = _run()
        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL", output)

    def test_no_additional_documents_configured_is_not_a_failure(self):
        with override_settings(KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=[]):
            exit_code, output = _run()
        self.assertEqual(exit_code, 0)

    def test_fail_fast_stops_after_the_first_failing_check(self):
        # Both the template dirs and the instructor documents check would fail here -
        # without --fail-fast both run; with it, only the first (template dirs, which
        # runs first in the checks list) should report.
        missing_dir = os.path.join(tempfile.gettempdir(), "definitely-not-a-real-theme-dir")
        broken_templates = [{**settings.TEMPLATES[0], "DIRS": [missing_dir]}]
        with override_settings(
            TEMPLATES=broken_templates,
            KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS=["pdf/does-not-exist.pdf"],
        ):
            _, without_fail_fast = _run()
            _, with_fail_fast = _run(fail_fast=True)

        self.assertIn("does-not-exist.pdf", without_fail_fast)
        self.assertNotIn("does-not-exist.pdf", with_fail_fast)
