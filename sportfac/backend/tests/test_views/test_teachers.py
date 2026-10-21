from bs4 import BeautifulSoup
from django.urls import reverse

from profiles.models import SchoolYear
from schools.models import Building
from schools.models import Teacher

from .base import BackendTestBase


class TeachersViewsTests(BackendTestBase):
    def test_list(self):
        url = reverse("backend:teacher-list")
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse("backend:teacher-create")
        self.generic_test_rights(url)

    def test_creation_fields_are_styled_and_allow_multiple_assignments(self):
        self.tenant_client.force_login(self.manager)
        year, _ = SchoolYear.objects.get_or_create(year=3)
        response = self.tenant_client.get(reverse("backend:teacher-create"))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        for name in ("first_name", "last_name", "email"):
            field = soup.select_one('[name="' + name + '"]')
            self.assertIn("form-control", field["class"])
            self.assertTrue(field.get("id"))
        self.assertIsNotNone(soup.select_one('input[type="checkbox"][name="years"][value="' + str(year.pk) + '"]'))
        self.assertIsNotNone(soup.select_one('select[name="buildings"][multiple]'))
        self.assertContains(response, "Affectation scolaire")
        self.assertContains(response, "Identité et contact")

    def test_create_saves_multiple_years_and_buildings(self):
        self.tenant_client.force_login(self.manager)
        years = [SchoolYear.objects.get_or_create(year=year)[0] for year in (3, 4)]
        buildings = [Building.objects.create(name=name) for name in ("Collège A", "Collège B")]
        response = self.tenant_client.post(
            reverse("backend:teacher-create"),
            {
                "first_name": "Marie",
                "last_name": "Martin",
                "email": "marie@example.com",
                "years": [year.pk for year in years],
                "buildings": [building.pk for building in buildings],
            },
        )
        self.assertEqual(response.status_code, 302)
        teacher = Teacher.objects.get(email="marie@example.com")
        self.assertCountEqual(teacher.years.all(), years)
        self.assertCountEqual(teacher.buildings.all(), buildings)

    def test_invalid_creation_preserves_selected_assignments(self):
        self.tenant_client.force_login(self.manager)
        year, _ = SchoolYear.objects.get_or_create(year=3)
        building = Building.objects.create(name="Collège A")
        response = self.tenant_client.post(
            reverse("backend:teacher-create"),
            {
                "first_name": "Marie",
                "last_name": "",
                "years": [year.pk],
                "buildings": [building.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        self.assertIsNotNone(soup.select_one('input[name="years"][checked]'))
        self.assertEqual(soup.select_one('select[name="buildings"] option[selected]')["value"], str(building.pk))
        self.assertFalse(Teacher.objects.filter(first_name="Marie").exists())

    def test_building_creation_uses_styled_widgets(self):
        self.tenant_client.force_login(self.manager)
        response = self.tenant_client.get(reverse("backend:building-create"))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "html.parser")
        for name in ("name", "address", "zipcode", "city", "country"):
            self.assertIn("form-control", soup.select_one('[name="' + name + '"]')["class"])
