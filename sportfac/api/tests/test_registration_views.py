from django.contrib.auth import get_user_model
from django.urls import reverse

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory, RegistrationFactory
from rest_framework import status

from sportfac.utils import TenantTestCase

from .utils import UserMixin


User = get_user_model()


class RegistrationViewSetTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.parent_user = FamilyUserFactory()
        self.unrelated_user = FamilyUserFactory()

        # Assign children to parent user
        self.child1 = ChildFactory(family=self.parent_user)
        self.child2 = ChildFactory(family=self.parent_user)

        # Create a child not related to the parent user
        self.unrelated_child = ChildFactory()

        # Create registrations for parent's children
        self.course = CourseFactory()
        self.registration1 = RegistrationFactory(child=self.child1, course=self.course)
        self.registration2 = RegistrationFactory(child=self.child2, course=self.course)

        # Create a registration for the unrelated child
        self.unrelated_registration = RegistrationFactory(child=self.unrelated_child)
        self.url = reverse("api:registration-list")  # Assumes registration-list is the viewset's name in urls.py

    def test_create_registration(self):
        """Test creating a single registration"""
        self.login(self.parent_user)
        course = CourseFactory()
        data = {
            "child": self.child1.id,
            "course": course.id,
        }
        response = self.tenant_client.post(self.url, data, format="json")
        # Assert response status and content
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["child"], self.child1.id)
        self.assertEqual(response.data["course"], course.id)
        registration = Registration.objects.get(pk=response.data["id"])
        self.assertEqual(registration.child, self.child1)
        self.assertEqual(registration.course, course)

    def test_parent_user_access(self):
        """Test that parent user can only see registrations related to their children"""
        self.client.force_login(self.parent_user)
        response = self.client.get(self.url)

        # Assert that parent user sees only their own children's registrations
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn(self.registration1.id, [reg["id"] for reg in response.data])
        self.assertIn(self.registration2.id, [reg["id"] for reg in response.data])

        # Ensure the unrelated registration is not visible
        self.assertNotIn(self.unrelated_registration.id, [reg["id"] for reg in response.data])

    def test_unrelated_user_no_access(self):
        """Test that an unrelated user cannot see registrations they don't have rights to"""
        self.client.force_login(self.unrelated_user)
        response = self.client.get(self.url)

        # Unrelated user should see no registrations
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_permission_denied_without_authentication(self):
        """Test that unauthenticated users cannot access the viewset"""
        response = self.client.get(self.url)
        # Should return 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
