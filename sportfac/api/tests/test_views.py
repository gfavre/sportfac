import datetime
import json
import logging

import faker
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from activities.cache import get_structural_activities_cache_key
from activities.tests.factories import CourseFactory
from api.serializers import ChildrenSerializer
from profiles.tests.factories import FamilyUserFactory
from profiles.tests.factories import SchoolYearFactory
from registrations.models import Child
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
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
        # A plain year subtraction over/under-counts by one whenever the birthday hasn't
        # happened yet this year - relativedelta accounts for month/day, matching how
        # Course.save() itself derives min_birth_date/max_birth_date from age_min/age_max.
        self.age = relativedelta(datetime.date.today(), self.birth_date).years
        # Course.save() derives start_date (and min/max_birth_date) from sessions when
        # KEPCHUP_EXPLICIT_SESSION_DATES is on, wiping the date given below since this
        # course has no sessions - force it off just for creation.
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
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

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
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

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_filter_by_age_boundary_dates(self):
        # self.course has age_min == age_max == self.age, so min/max_birth_date form an
        # exact 1-year window. Both edges are inclusive (matches the original
        # min_birth_date__gte / max_birth_date__lte DB filter) - this pins the Python
        # reimplementation of that filter (ActivityViewSet._course_matches_birth_date)
        # against the same boundary semantics.
        min_birth_date = self.course.min_birth_date
        max_birth_date = self.course.max_birth_date
        url = reverse("api:activity-list")

        cases = [
            ("exact upper bound", min_birth_date, True),
            ("exact lower bound", max_birth_date, True),
            ("one day too young", min_birth_date + datetime.timedelta(days=1), False),
            ("one day too old", max_birth_date - datetime.timedelta(days=1), False),
        ]
        for label, birth_date, expect_match in cases:
            response = self.tenant_client.get(url + f"?birth_date={birth_date.isoformat()}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), 1 if expect_match else 0, label)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_filter_by_age_unrestricted_course_always_matches(self):
        CourseFactory(activity=self.course.activity, age_min=None, age_max=None, start_date=datetime.date.today())
        url = reverse("api:activity-list") + "?birth_date=1900-01-01"
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        # self.course (age-restricted) doesn't match a 1900 birth_date - only the
        # unrestricted course should remain under this activity.
        self.assertEqual(len(response.data[0]["courses"]), 1)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_filter_by_age_excludes_activities_with_no_matching_course(self):
        CourseFactory(age_min=self.age + 5, age_max=self.age + 6, start_date=datetime.date.today())
        url = reverse("api:activity-list") + f"?birth_date={self.birth_date.isoformat()}"
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        # the new course's own activity has zero matching courses, so it must not appear
        self.assertEqual(len(response.data), 1)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_filter_by_age_partial_match_within_activity(self):
        CourseFactory(
            activity=self.course.activity,
            age_min=self.age + 5,
            age_max=self.age + 6,
            start_date=datetime.date.today(),
        )
        url = reverse("api:activity-list") + f"?birth_date={self.birth_date.isoformat()}"
        response = self.tenant_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(len(response.data[0]["courses"]), 1)
        self.assertEqual(response.data[0]["courses"][0]["id"], self.course.id)

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True)
    def test_filter_by_school_year_boundary(self):
        url = reverse("api:activity-list")
        for year, expect_match in [
            (self.school_year, True),
            (self.school_year - 1, False),
            (self.school_year + 1, False),
        ]:
            response = self.tenant_client.get(url + f"?year={year}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data), 1 if expect_match else 0, f"year={year}")


class ActivityViewSetCachingTests(TenantTestCase):
    """Covers the shared structural cache backing ActivityViewSet.list() and its
    invalidation via activities.signals - see api/views/activities_views.py and
    activities/signals.py."""

    def setUp(self):
        super().setUp()
        self.course = CourseFactory(visible=True)
        self.cache_key = get_structural_activities_cache_key(self.tenant.id)
        cache.delete(self.cache_key)
        self.url = reverse("api:activity-list")

    def tearDown(self):
        cache.delete(self.cache_key)
        super().tearDown()

    def test_list_populates_the_structural_cache(self):
        self.assertIsNone(cache.get(self.cache_key))
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(cache.get(self.cache_key))

    def test_list_reuses_the_cache_for_different_children(self):
        self.tenant_client.get(self.url + "?birth_date=2015-01-01")
        cached_after_first = cache.get(self.cache_key)
        self.assertIsNotNone(cached_after_first)
        # A completely different child (different birth_date) must still hit the same
        # cached structural payload - eligibility filtering happens in Python afterwards,
        # not by varying the cache key per child.
        self.tenant_client.get(self.url + "?birth_date=2010-01-01")
        self.assertEqual(cache.get(self.cache_key), cached_after_first)

    def test_creating_a_course_invalidates_the_cache(self):
        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        CourseFactory(visible=True)
        self.assertIsNone(cache.get(self.cache_key))

    def test_deleting_a_course_invalidates_the_cache(self):
        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        self.course.delete()
        self.assertIsNone(cache.get(self.cache_key))

    def test_editing_an_activity_invalidates_the_cache(self):
        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        self.course.activity.name = "Nouveau nom"
        self.course.activity.save()
        self.assertIsNone(cache.get(self.cache_key))

    def test_editing_a_session_invalidates_the_cache(self):
        from absences.tests.factories import SessionFactory

        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        SessionFactory(course=self.course)
        self.assertIsNone(cache.get(self.cache_key))

    def test_registration_does_not_invalidate_the_cache(self):
        # A registration only ever touches Course.nb_participants (via
        # Course.update_registrations(), save(update_fields=["nb_participants"])) - that
        # field isn't part of the cached structural payload, so it must not bust this
        # cache, or it would get invalidated on nearly every write during a rush.
        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        self.course.nb_participants += 1
        self.course.save(update_fields=["nb_participants"])
        self.assertIsNotNone(cache.get(self.cache_key))

    def test_unrelated_course_field_change_invalidates_the_cache(self):
        self.tenant_client.get(self.url)
        self.assertIsNotNone(cache.get(self.cache_key))
        self.course.name = "Nouveau nom de cours"
        self.course.save(update_fields=["name"])
        self.assertIsNone(cache.get(self.cache_key))


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
        # Course.save() derives start_date (and min/max_birth_date) from sessions when
        # KEPCHUP_EXPLICIT_SESSION_DATES is on, wiping them since this course has no
        # sessions - force it off just for creation.
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
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
        with override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False):
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
