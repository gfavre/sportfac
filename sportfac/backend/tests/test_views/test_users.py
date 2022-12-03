# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.urls import reverse

from .base import BackendTestBase


class UsersViewsTests(BackendTestBase):
    def test_list(self):
        url = reverse("backend:user-list")
        self.generic_test_rights(url)

    def test_managers_list(self):
        url = reverse("backend:manager-list")
        self.generic_test_rights(url)

    def test_instructors_list(self):
        url = reverse("backend:instructor-list")
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse("backend:user-create")
        self.generic_test_rights(url)

    def test_create_manager(self):
        url = reverse("backend:manager-create")
        self.generic_test_rights(url)
