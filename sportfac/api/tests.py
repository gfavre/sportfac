from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase, APIClient

from activities.tests.factories import ActivityFactory
from profiles.tests.factories.users import SchoolYearFactory, TeacherFactory

class ActivityAPITests(APITestCase):
    def setUp(self):
        self.activity = ActivityFactory()
    
    def test_list(self):
        url = reverse("api:activity-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)        


class TeacherAPITests(APITestCase):
    def setUp(self):
        self.year = SchoolYearFactory()
        self.teacher = TeacherFactory()
        self.teacher.years.add(self.year)
    
    def test_list(self):
        url = reverse("api:teacher-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)