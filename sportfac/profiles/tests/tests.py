"""
Tests for profiles app.
"""
from __future__ import absolute_import

from sportfac.utils import TenantTestCase

from .factories import FamilyUserFactory


class FamilyUserTestCase(TenantTestCase):
    def setUp(self):
        super(FamilyUserTestCase, self).setUp()
        self.superuser = FamilyUserFactory(is_superuser=True, is_admin=True)
        self.admin = FamilyUserFactory(is_admin=True)
        self.manager = FamilyUserFactory(is_manager=False)
        self.user = FamilyUserFactory()
