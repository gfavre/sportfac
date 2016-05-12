"""
Tests for profiles app.
"""
from datetime import time
from django.contrib.auth.models import Group

from .factories import FamilyUserFactory
from backend import MANAGERS_GROUP
from sportfac.utils import TenantTestCase


        
class FamilyUserTestCase(TenantTestCase):

    def setUp(self):
        super(FamilyUserTestCase, self).setUp()
        self.superuser = FamilyUserFactory(is_superuser=True, is_admin=True)
        self.admin = FamilyUserFactory(is_admin=True)
        self.manager = FamilyUserFactory()
        managers, created = Group.objects.get_or_create(name=MANAGERS_GROUP)
        self.manager.groups.add(managers)
        self.user = FamilyUserFactory()
    
    def test_manager_rights(self):
        self.assertTrue(self.superuser.is_manager)
        self.assertTrue(self.admin.is_manager)
        self.assertTrue(self.manager.is_manager)
        self.assertFalse(self.user.is_manager)
           
