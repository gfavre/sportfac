import json

from django.urls import reverse
from django.utils.translation import override

from backend.views.user_views import ValidateIBANView

from .base import BackendTestBase


class UsersViewsTests(BackendTestBase):
    def test_iban_errors_in_french(self):
        for value, message in [
            ("CH93", "Un IBAN CH doit contenir 21 caractères."),
            ("ZZ9300762011623852957", "Le code pays « ZZ » n’est pas valide pour un IBAN."),
            ("CH9300762011623852958", "Cet IBAN n’est pas valide. Vérifiez les caractères saisis."),
        ]:
            with self.subTest(value=value), override("fr"):
                request = self.factory.post("/", {"iban": value})
                response = ValidateIBANView().post(request)
                self.assertEqual(json.loads(response.content)["message"], message)

    def test_list(self):
        url = reverse("backend:user-list")
        self.generic_test_rights(url)

    def test_managers_list(self):
        url = reverse("backend:manager-list")
        self.generic_test_rights(url)

    def test_instructors_list(self):
        url = reverse("backend:instructor-list")
        self.generic_test_rights(url)

    def test_create(self):
        url = reverse("backend:user-create")
        self.generic_test_rights(url)

    def test_create_manager(self):
        url = reverse("backend:manager-create")
        self.generic_test_rights(url)

    def test_create_instructor_datepicker_assets(self):
        url = reverse("backend:instructor-create")
        self.generic_test_rights(url)
        response = self.tenant_client.get(url)
        self.assertContains(response, 'name="birth_date"')
        self.assertContains(response, "datepicker-widget.js", count=1)
        self.assertNotContains(response, "js/vendor/bootstrap-datetimepicker.min.js")
        self.assertNotContains(response, "js/vendor/moment-with-locales.min.js")

    def test_iban_validation(self):
        url = reverse("backend:validate-iban")
        self.assertEqual(self.tenant_client.post(url, {"iban": "invalid"}).status_code, 302)
        self.tenant_client.force_login(self.user)
        self.assertEqual(self.tenant_client.post(url, {"iban": "invalid"}).status_code, 302)
        self.tenant_client.force_login(self.manager)
        for value, valid in [
            ("", True),
            ("ch93 0076 2011 6238 5295 7", True),
            ("CH9300762011623852958", False),
            ("CH93", False),
            ("invalid", False),
        ]:
            with self.subTest(value=value):
                response = self.tenant_client.post(url, {"iban": value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["valid"], valid)

    def test_edit_user_uses_grouped_layout(self):
        url = reverse("backend:user-update", args=[self.user.pk])
        self.generic_test_rights(url)
        response = self.tenant_client.get(url)
        self.assertNotContains(response, 'class="form-horizontal"')
        self.assertNotContains(response, 'name="password1"')
        self.assertContains(response, reverse("backend:password-change", args=[self.user.pk]))
        content = response.content.decode()
        self.assertLess(content.index('name="first_name"'), content.index('name="email"'))
        self.assertContains(response, 'class="col-sm-6"')
