# -*- coding: utf-8 -*-
from django.urls import reverse

from activities.tests.factories import CourseFactory
from registrations.tests.factories import ChildFactory, RegistrationFactory

from .base import BackendTestBase


class RegistrationsViewsTests(BackendTestBase):
    def setUp(self):
        super(RegistrationsViewsTests, self).setUp()
        self.child = ChildFactory()
        self.course = CourseFactory()
        self.registration = RegistrationFactory(child=self.child, course=self.course)

    def test_list(self):
        url = reverse('backend:registration-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:registration-create')
        self.generic_test_rights(url)
