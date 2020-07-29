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
    
    def test_manager_rights(self):
        self.assertTrue(self.superuser.is_manager)
        self.assertTrue(self.admin.is_manager)
        self.assertTrue(self.manager.is_manager)
        self.assertFalse(self.user.is_manager)
           
