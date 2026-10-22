from datetime import date

from django.urls import reverse

from activities.tests.factories import CourseFactory
from api.tests.utils import UserMixin
from profiles.forms import InstructorForm
from profiles.forms import UserForm
from profiles.tests.factories import FamilyUserFactory
from profiles.utils import invalidate_user_cache
from sportfac.utils import TenantTestCase


class AccountLayoutTests(UserMixin, TenantTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("profiles:profiles_account")
        self.user = FamilyUserFactory(bank_name="Banque moniteur", is_mep=True)
        self.data = {
            "email": self.user.email,
            "first_name": "Camille",
            "last_name": "Exemple",
            "address": "Rue du Lac 3",
            "zipcode": "1800",
            "city": "Vevey",
            "country": "CH",
            "private_phone": "+41791234567",
        }

    def make_instructor(self):
        CourseFactory(instructors=[self.user])
        invalidate_user_cache(self.user.pk, "is_instructor")

    def test_login_required_for_get_and_post(self):
        for method in (self.tenant_client.get, self.tenant_client.post):
            self.assertEqual(method(self.url).status_code, 302)

    def test_member_keeps_user_form_with_vertical_sections(self):
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIs(type(response.context["form"]), UserForm)
        self.assertContains(response, 'class="account-profile-form"')
        self.assertContains(response, "profiles/account.css")
        self.assertContains(response, "Éditer le compte")
        self.assertNotContains(response, "col-sm-offset-3")
        self.assertNotContains(response, 'name="iban"')
        self.assertEqual(response.context["form"].helper.label_class, "")
        self.assertEqual(response.context["form"].helper.field_class, "")

    def test_instructor_keeps_professional_fields_and_media(self):
        self.make_instructor()
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIs(type(response.context["form"]), InstructorForm)
        for name in ("iban", "bank_name", "birth_date", "ahv", "js_identifier", "is_mep", "phone_public"):
            self.assertContains(response, f'name="{name}"')
        self.assertContains(response, "backend/js/iban-validation.js", count=1)
        self.assertEqual(response.context["form"].helper.label_class, "")

    def test_member_save_preserves_role_specific_data_and_password(self):
        original_password = self.user.password
        self.login(self.user)
        response = self.tenant_client.post(self.url, {**self.data, "bank_name": "Ignorer", "is_mep": ""})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Camille")
        self.assertEqual(self.user.bank_name, "Banque moniteur")
        self.assertTrue(self.user.is_mep)
        self.assertEqual(self.user.password, original_password)

    def test_invalid_form_keeps_new_layout_and_errors(self):
        self.login(self.user)
        response = self.tenant_client.post(self.url, {**self.data, "email": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertContains(response, 'class="account-profile-form"')

    def test_instructor_can_still_save_professional_details(self):
        self.make_instructor()
        self.login(self.user)
        response = self.tenant_client.post(self.url, {**self.data, "bank_name": "Nouvelle banque", "is_mep": "on"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bank_name, "Nouvelle banque")
        self.assertTrue(self.user.is_mep)

    def test_manager_without_instructor_role_keeps_member_form(self):
        self.user.is_manager = True
        self.user.save()
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIs(type(response.context["form"]), UserForm)

    def test_instructor_birth_date_uses_swiss_format_and_saves_a_date(self):
        self.make_instructor()
        self.user.birth_date = date(1985, 4, 23)
        self.user.save()
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="23.04.1985"')
        self.assertContains(response, 'placeholder="JJ.MM.AAAA"')
        self.assertContains(response, "js/vendor/bootstrap-datepicker.js")
        self.assertContains(response, "profiles/account.js")
        self.assertNotContains(response, "bootstrap-datetimepicker.min.js")
        self.assertNotContains(response, "datepicker-widget.js")
        response = self.tenant_client.post(self.url, {**self.data, "birth_date": "12.06.1987"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.birth_date, date(1987, 6, 12))

    def test_invalid_birth_date_keeps_error_in_account_form(self):
        self.make_instructor()
        self.login(self.user)
        for value in ("31.02.1987", "06/12/1987", "1987-06-12"):
            with self.subTest(value=value):
                response = self.tenant_client.post(self.url, {**self.data, "birth_date": value})
                self.assertEqual(response.status_code, 200)
                self.assertIn("birth_date", response.context["form"].errors)

    def test_nationality_prioritizes_switzerland_without_changing_saved_choice(self):
        self.make_instructor()
        self.user.nationality = "FR"
        self.user.save()
        self.login(self.user)
        response = self.tenant_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        choices = list(response.context["form"].fields["nationality"].choices)
        self.assertEqual(choices[0][0], "CH")
        self.assertEqual(choices[1], ("", "---"))
        self.assertEqual(sum(code == "CH" for code, label in choices), 2)
        self.assertEqual(str(response.context["form"]["nationality"].value()), "FR")
        response = self.tenant_client.post(self.url, {**self.data, "nationality": "DE"})
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.nationality.code, "DE")
