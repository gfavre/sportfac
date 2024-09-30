from unittest.mock import MagicMock, patch

from django.conf import settings

from sportfac.utils import TenantTestCase

from ..models import Course  # Replace with your actual Course model path
from ..tasks import send_places_available_reminder  # Replace with the actual import path
from .factories import CourseFactory


class SendPlacesAvailableReminderTest(TenantTestCase):
    def setUp(self):
        # Create mock Course instance
        self.course_mock = MagicMock(spec=Course)
        self.course_mock.id = 1
        self.course = CourseFactory()

    @patch("activities.tasks.send_mail.delay")
    @patch("activities.tasks.translation.activate")
    @patch("activities.tasks.connection.set_tenant")
    @patch("activities.tasks.Domain.objects.filter")
    def test_send_places_available_reminder_success(
        self, mock_domain_filter, mock_set_tenant, mock_activate, mock_send_mail
    ):
        """Test the successful flow of the send_places_available_reminder task."""
        # Set settings to allow waiting lists
        settings.KEPCHUP_ENABLE_WAITING_LISTS = True

        # Mock dependencies
        mock_domain_filter.return_value.first.return_value.tenant = MagicMock()

        # Call the task
        send_places_available_reminder(course_pk=self.course.pk)

        # Assert tenant switching and language activation
        mock_activate.assert_called()
        mock_set_tenant.assert_called()
        # Assert that the email was sent
        mock_send_mail.assert_called_once()
        self.course.refresh_from_db()
        self.assertIsNotNone(self.course.places_available_reminder_sent_on)

    @patch("activities.tasks.send_mail.delay")
    def test_send_places_available_reminder_disabled(self, mock_send_mail):
        """Test that the task exits early when KEPCHUP_WAITING_LISTS is False."""
        # Set settings to disable waiting lists
        settings.KEPCHUP_ENABLE_WAITING_LISTS = False
        # Call the task
        result = send_places_available_reminder(course_pk=self.course.pk)
        mock_send_mail.assert_not_called()
        # Check that the task returned False
        self.assertFalse(result)

    @patch("activities.tasks.send_mail.delay")
    @patch("activities.tasks.translation.activate")
    @patch("activities.tasks.translation.get_language")
    def test_language_switching(self, mock_get_language, mock_activate, mock_send_mail):
        """Test that the task correctly activates and restores the language."""
        # Mock the initial language
        mock_get_language.return_value = "en"

        # Call the task with a different language
        send_places_available_reminder(course_pk=self.course.pk, language="fr")

        # Assert that the language was switched to "fr"
        mock_activate.assert_any_call("fr-CH")

        # Assert that the original language was restored
        mock_activate.assert_any_call("en")

    @patch("activities.tasks.send_mail.delay")
    @patch("activities.tasks.YearTenant.objects.get")
    @patch("activities.tasks.connection.set_tenant")
    def test_tenant_switching_with_tenant_pk(self, mock_set_tenant, mock_tenant_get, mock_send_mail):
        """Test that the correct tenant is set based on tenant_pk."""
        # Mock tenant
        tenant_mock = MagicMock()
        mock_tenant_get.return_value = tenant_mock

        # Call the task with tenant_pk
        send_places_available_reminder(course_pk=self.course.pk, tenant_pk=5)

        # Assert that the correct tenant is set
        mock_tenant_get.assert_called_once_with(pk=5)
        mock_set_tenant.assert_called_once_with(tenant_mock)

    @patch("activities.tasks.send_mail.delay")
    @patch("activities.tasks.Domain.objects.filter")
    @patch("activities.tasks.connection.set_tenant")
    def test_tenant_switching_with_current_domain(self, mock_set_tenant, mock_domain_filter, mock_send_mail):
        """Test that the correct tenant is set based on the current domain when no tenant_pk is provided."""
        # Mock current domain and tenant
        tenant_mock = MagicMock()
        mock_domain_filter.return_value.first.return_value.tenant = tenant_mock

        # Call the task without tenant_pk
        send_places_available_reminder(course_pk=self.course.pk, tenant_pk=None)

        # Assert that the current domain's tenant is set
        mock_domain_filter.assert_called_once_with(is_current=True)
        mock_set_tenant.assert_called_once_with(tenant_mock)
