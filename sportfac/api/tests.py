from django.core.urlresolvers import reverse

import faker
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase, APIClient

from activities.tests.factories import ActivityFactory, CourseFactory
from profiles.models import Child
from profiles.tests.factories.users import ChildFactory, FamilyUserFactory, SchoolYearFactory, TeacherFactory, DEFAULT_PASS
from profiles.tests.factories.registrations import RegistrationFactory
from api.serializers import ChildrenSerializer

fake = faker.Factory.create('fr_CH')

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
        self.admin = FamilyUserFactory()
        self.admin.is_manager = True

    def test_rights(self):
        url = reverse("api:child-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        url = reverse("api:child-list")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)
        url = reverse("api:child-detail", kwargs={'pk': self.children1[0].pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.login(self.user2)
        response = self.client.get(url)
        # when user is known but child is not his, we purposely do not inform 
        # him of child existence
        self.assertEqual(response.status_code, 404)
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
    
    def test_list(self):
        url = reverse("api:child-list")
        self.login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), self.user1.children.count())
        self.login(self.user2)
        response = self.client.get(url)
        self.assertEqual(len(response.data), self.user2.children.count())

    def test_create(self):
        url = reverse("api:child-list")
        self.login(self.user1)
        new_child = {
            'first_name': fake.first_name(),
            'last_name': self.user1.last_name,
            'sex': Child.SEX.F,
            'nationality': Child.NATIONALITY.CH,
            'language': Child.LANGUAGE.F,
            'birth_date': fake.date(),
            'school_year': self.children2[0].school_year.year,
            'teacher': self.children2[0].teacher.pk
            
        }
        response = self.client.post(url, new_child, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.user1.children.count(), 4)
        del(new_child['first_name'])
        response = self.client.post(url, new_child, format='json')
        self.assertEqual(response.status_code, 400)
    
    def test_detail(self):
        url = reverse("api:child-detail", kwargs={'pk': self.children1[0].pk})
        self.login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_update(self):
        child = self.children1[0]
        url = reverse("api:child-detail", kwargs={'pk': child.pk})
        self.login(self.user1)
        new_name = fake.last_name()
        child.last_name = new_name
        
        response = self.client.put(url, ChildrenSerializer(child).data)
        self.assertEqual(response.status_code, 200)
        child.refresh_from_db()
        self.assertEqual(child.last_name, new_name)

    def test_delete(self):
        child = self.children1[0]
        url = reverse("api:child-detail", kwargs={'pk': child.pk})
        self.login(self.user1)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.user1.children.count(), 2)


class RegistrationAPITests(UserAPITestCase):
    def setUp(self):
        self.year = SchoolYearFactory()
        self.course = CourseFactory()
        self.child1 = ChildFactory(school_year=self.year)
        self.child2 = ChildFactory(school_year=self.year)
        self.reg1 = RegistrationFactory(course=self.course, child=self.child1)
        self.reg2 = RegistrationFactory(course=self.course, child=self.child2)
        self.admin = FamilyUserFactory()
        self.admin.is_manager = True
            
    def test_rights(self):
        url = reverse("api:registration-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 403)
        url = reverse("api:registration-detail", kwargs={'pk': self.reg1.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 403)
        self.login(self.child2.family)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        response = self.client.put(url, {})
        self.assertEqual(response.status_code, 404)

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
    
    def _test_create(self, user):
        url = reverse("api:registration-list")
        self.login(user)
        course2 = CourseFactory()
        response = self.client.post(url, {'child': self.child1.pk, 'course': course2.pk})
        self.assertEqual(response.status_code, 201)
        response = self.client.post(url, {'child': self.child1.pk, 'course': course2.pk})
        self.assertEqual(response.status_code, 400)
    
    def test_user_registers(self):
        self._test_create(self.child1.family)
    
    def test_admin_registers(self):
        self._test_create(self.admin)

    def test_detail(self):
        url = reverse("api:registration-detail", kwargs={'pk': self.reg1.pk})
        self.login(self.child1.family)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.login(self.admin)
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


