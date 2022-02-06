"""
Tests for profiles app.
"""
from .factories import FamilyUserFactory
from sportfac.utils import TenantTestCase


        
class FamilyUserTestCase(TenantTestCase):

    def setUp(self):
        super(FamilyUserTestCase, self).setUp()
        self.superuser = FamilyUserFactory(is_superuser=True, is_admin=True)
        self.admin = FamilyUserFactory(is_admin=True)
        self.manager = FamilyUserFactory(is_manager=False)
        self.user = FamilyUserFactory()
