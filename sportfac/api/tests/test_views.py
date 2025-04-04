import datetime
import json
import logging

from django.test import override_settings
from django.urls import reverse

import faker

from activities.tests.factories import CourseFactory
from api.serializers import ChildrenSerializer
from profiles.tests.factories import FamilyUserFactory, SchoolYearFactory
from registrations.models import Child
from registrations.tests.factories import ChildFactory, RegistrationFactory
from schools.tests.factories import TeacherFactory
from sportfac.utils import TenantTestCase
from .utils import UserMixin


fake = faker.Factory.create("fr_CH")

logger = logging.getLogger("django.request")
logger.disabled = True


class ActivityAPITests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.school_year = 3
        self.birth_date = fake.date_between(start_date="-10y", end_date="-5y")
        self.age = datetime.date.today().year - self.birth_date.year
        self.course = CourseFactory(
            schoolyear_min=self.school_year,
            schoolyear_max=self.school_year,
            age_min=self.age,
            age_max=self.age,
            start_date=datetime.date.today(),
        )

    def test_list(self):
        url = reverse("api:activity-list")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_filter_by_school_year(self):
        CourseFactory(schoolyear_min=self.school_year - 1, schoolyear_max=self.school_year + 1)  # overlap
        CourseFactory(schoolyear_min=self.school_year + 1, schoolyear_max=self.school_year + 2)  # out of range
        url = reverse("api:activity-list") + f"?year={self.school_year}"
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False)
    def test_filter_by_age(self):
        CourseFactory(
            age_min=self.age + 1,
            age_max=self.age + 2,
            start_date=datetime.date.today(),
        )  # too young
        CourseFactory(
            age_min=self.age - 2,
            age_max=self.age - 1,
            start_date=datetime.date.today(),
        )  # too old
        url = reverse("api:activity-list") + f"?birth_date={self.birth_date.isoformat()}"
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)


class CoursesAPITests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.course = CourseFactory()

    def test_list(self):
        url = reverse("api:course-list")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)


class ChildrenAPITests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.year = SchoolYearFactory()
        self.user1 = FamilyUserFactory()
        self.children1 = ChildFactory.create_batch(size=3, school_year=self.year, family=self.user1)
        self.user2 = FamilyUserFactory()
        self.children2 = ChildFactory.create_batch(size=2, school_year=self.year, family=self.user2)
        self.admin = FamilyUserFactory()
        self.admin.is_manager = True
        self.teacher = TeacherFactory()

    def test_rights(self):
        url = reverse("api:child-list")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 403)
        url = reverse("api:child-list")
        response = self.tenant_client.post(url, {})
        self.assertEqual(response.status_code, 403)
        url = reverse("api:child-detail", kwargs={"pk": self.children1[0].pk})
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.tenant_client.put(url, {})
        self.assertEqual(response.status_code, 403)
        response = self.tenant_client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.login(self.user2)
        response = self.tenant_client.get(url)
        # when user is known but child is not his, we purposely do not inform
        # him of child existence
        self.assertEqual(response.status_code, 404)
        response = self.tenant_client.put(url, {})
        self.assertEqual(response.status_code, 404)
        response = self.tenant_client.delete(url)
        self.assertEqual(response.status_code, 404)

    def test_list(self):
        url = reverse("api:child-list")
        self.login(self.user1)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), self.user1.children.count())
        self.login(self.user2)
        response = self.tenant_client.get(url)
        self.assertEqual(len(response.data), self.user2.children.count())

    def test_create(self):
        url = reverse("api:child-list")
        self.login(self.user1)
        new_child = {
            "first_name": fake.first_name(),
            "last_name": self.user1.last_name,
            "sex": Child.SEX.F,
            "nationality": Child.NATIONALITY.CH,
            "language": Child.LANGUAGE.F,
            "birth_date": fake.date(),
            "school_year": self.children2[0].school_year.year,
            "teacher": self.teacher.pk,
        }
        response = self.tenant_client.post(url, new_child, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.user1.children.count(), 4)
        del new_child["first_name"]
        response = self.tenant_client.post(url, new_child, format="json")
        self.assertEqual(response.status_code, 400)

    def test_detail(self):
        url = reverse("api:child-detail", kwargs={"pk": self.children1[0].pk})
        self.login(self.user1)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.login(self.admin)

    def test_update(self):
        child = self.children1[0]
        url = reverse("api:child-detail", kwargs={"pk": child.pk})
        self.login(self.user1)
        new_name = fake.last_name()
        child.last_name = new_name
        data = ChildrenSerializer(child).data
        response = self.tenant_client.put(url, json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        child.refresh_from_db()
        self.assertEqual(child.last_name, new_name)

    def test_delete(self):
        child = self.children1[0]
        url = reverse("api:child-detail", kwargs={"pk": child.pk})
        self.login(self.user1)
        response = self.tenant_client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.user1.children.count(), 2)


class RegistrationAPITests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.year = SchoolYearFactory()
        self.course = CourseFactory(schoolyear_min=self.year.year, schoolyear_max=self.year.year)
        self.child1 = ChildFactory(school_year=self.year)
        self.child2 = ChildFactory(school_year=self.year)
        self.reg1 = RegistrationFactory(course=self.course, child=self.child1)
        self.reg2 = RegistrationFactory(course=self.course, child=self.child2)
        self.admin = FamilyUserFactory()
        self.admin.is_manager = True

    def test_rights(self):
        url = reverse("api:registration-list")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.tenant_client.post(url, {})
        self.assertEqual(response.status_code, 403)
        url = reverse("api:registration-detail", kwargs={"pk": self.reg1.pk})
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.tenant_client.delete(url)
        self.assertEqual(response.status_code, 403)
        response = self.tenant_client.put(url, {})
        self.assertEqual(response.status_code, 403)
        self.login(self.child2.family)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 404)
        response = self.tenant_client.delete(url)
        self.assertEqual(response.status_code, 404)
        response = self.tenant_client.put(url, {})
        self.assertEqual(response.status_code, 404)

    def test_list(self):
        url = reverse("api:registration-list")
        self.login(self.child1.family)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["child"], self.child1.pk)
        self.assertEqual(response.data[0]["course"], self.course.pk)

        self.login(self.child2.family)
        response = self.tenant_client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["child"], self.child2.pk)
        self.assertEqual(response.data[0]["course"], self.course.pk)

    def _test_create(self, user):
        url = reverse("api:registration-list")
        self.login(user)
        course2 = CourseFactory(
            schoolyear_min=self.year.year,
            schoolyear_max=self.year.year,
        )
        response = self.tenant_client.post(url, {"child": self.child1.pk, "course": course2.pk})
        self.assertEqual(response.status_code, 201)
        response = self.tenant_client.post(url, {"child": self.child1.pk, "course": course2.pk})
        self.assertEqual(response.status_code, 400)

    def test_user_registers(self):
        self._test_create(self.child1.family)

    def test_admin_registers(self):
        self._test_create(self.admin)

    def test_detail(self):
        url = reverse("api:registration-detail", kwargs={"pk": self.reg1.pk})
        self.login(self.child1.family)
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)


class TeacherAPITests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.year = SchoolYearFactory()
        self.teacher = TeacherFactory()
        self.teacher.years.add(self.year)

    def test_list(self):
        url = reverse("api:teacher-list")
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
