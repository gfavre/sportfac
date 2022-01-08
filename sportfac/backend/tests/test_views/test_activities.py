# -*- coding: utf-8 -*-
from django.urls import reverse

from .base import BackendTestBase
from activities.tests.factories import CourseFactory


class CourseViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:course-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:course-create')
        self.generic_test_rights(url)


class ActivitiesViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:activity-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:activity-create')
        self.generic_test_rights(url)