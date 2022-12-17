# -*- coding: utf-8 -*-
from activities.tests.factories import CourseFactory
from mock import patch
from registrations.models import Child, RegistrationsProfile
from registrations.tests.factories import ChildFactory

from sportfac.utils import TenantTestCase as TestCase

from ..models import FamilyUser
from .factories import FamilyUserFactory


class FamilyUserTests(TestCase):
    def setUp(self):
        super(FamilyUserTests, self).setUp()
        self.family_user = FamilyUserFactory()

    def test_save_creates_profile(self):
        if hasattr(self.family_user, "profile"):
            self.family_user.profile.delete()
        self.family_user.save(create_profile=True)
        self.assertEqual(RegistrationsProfile.objects.count(), 1)
        self.family_user.refresh_from_db()
        self.assertIsNotNone(self.family_user.profile)

    def test_soft_delete_unset_instructor(self):
        course = CourseFactory(instructors=[self.family_user])
        self.family_user.soft_delete()
        course.refresh_from_db()
        self.assertNotIn(self.family_user, course.instructors.all())

    def test_soft_delete_sets_inactive(self):
        self.family_user.soft_delete()
        self.assertFalse(self.family_user.is_active)

    def test_soft_delete_removes_children(self):
        ChildFactory(family=self.family_user)
        self.family_user.soft_delete()
        self.assertEqual(Child.objects.count(), 0)
