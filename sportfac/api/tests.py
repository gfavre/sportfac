from django.core.urlresolvers import reverse

from rest_framework.test import APITestCase, APIClient

from activities.tests.factories import ActivityFactory, CourseFactory
from profiles.tests.factories.users import ChildFactory, FamilyUserFactory, SchoolYearFactory, TeacherFactory, DEFAULT_PASS
from profiles.tests.factories.registrations import RegistrationFactory


class UserAPITestCase(APITestCase):
    def login(self, user):
        self.client.login(username=user.email, password=DEFAULT_PASS)


class ActivityAPITests(APITestCase):
    def setUp(self):
        self.activity = ActivityFactory()
    
    def test_list(self):
        url = reverse("api:activity-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class CoursesAPITests(APITestCase):
    def setUp(self):
        self.course = CourseFactory()
    
    def test_list(self):
        url = reverse("api:course-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ChildrenAPITests(UserAPITestCase):
    def setUp(self):
        self.year = SchoolYearFactory()
        self.user1 = FamilyUserFactory()
        self.children1 = ChildFactory.create_batch(size=3, school_year=self.year, family=self.user1)
        self.user2 = FamilyUserFactory()
        self.children2 = ChildFactory.create_batch(size=2, school_year=self.year, family=self.user2)

    def test_rights(self):
        url = reverse("api:child-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        url = reverse("api:child-list")
        self.login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), self.user1.children.count())
        self.login(self.user2)
        response = self.client.get(url)
        self.assertEqual(len(response.data), self.user2.children.count())


class RegistrationAPITests(UserAPITestCase):
    def setUp(self):
        self.year = SchoolYearFactory()
        self.course = CourseFactory()
        self.child1 = ChildFactory(school_year=self.year)
        self.child2 = ChildFactory(school_year=self.year)
        self.reg1 = RegistrationFactory(course=self.course, child=self.child1)
        self.reg2 = RegistrationFactory(course=self.course, child=self.child2)
        
    def test_rights(self):
        url = reverse("api:registration-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.login(self.child1.family)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list(self):
        url = reverse("api:registration-list")
        self.login(self.child1.family)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['child'], self.child1.pk)
        self.assertEqual(response.data[0]['course'], self.course.pk)

        self.login(self.child2.family)
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['child'], self.child2.pk)
        self.assertEqual(response.data[0]['course'], self.course.pk)



class TeacherAPITests(APITestCase):
    def setUp(self):
        self.year = SchoolYearFactory()
        self.teacher = TeacherFactory()
        self.teacher.years.add(self.year)
    
    def test_list(self):
        url = reverse("api:teacher-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


