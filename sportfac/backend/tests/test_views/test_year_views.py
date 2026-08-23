from unittest import mock

from django.urls import reverse

from profiles.tests.factories import DEFAULT_PASS

from .base import BackendTestBase


class LogEveryoneOutViewTest(BackendTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backend:log-everyone-out")

    def test_anonymous_denied(self):
        response = self.tenant_client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_basic_user_denied(self):
        self.tenant_client.login(username=self.user.email, password=DEFAULT_PASS)
        response = self.tenant_client.post(self.url)
        self.assertEqual(response.status_code, 302)

    @mock.patch("backend.views.year_views.log_everyone_out.delay")
    def test_manager_triggers_logout_task(self, mocked_delay):
        self.tenant_client.login(username=self.manager.email, password=DEFAULT_PASS)
        response = self.tenant_client.post(self.url)
        self.assertRedirects(response, reverse("backend:year-list"))
        self.assertTrue(mocked_delay.called)
