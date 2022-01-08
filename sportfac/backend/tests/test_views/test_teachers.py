# -*- coding: utf-8 -*-
from django.urls import reverse

from .base import BackendTestBase


class TeachersViewsTests(BackendTestBase):

    def test_list(self):
        url = reverse('backend:teacher-list')
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse('backend:teacher-create')
        self.generic_test_rights(url)
