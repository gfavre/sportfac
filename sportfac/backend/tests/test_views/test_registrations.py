from datetime import date
from unittest import mock
from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.formsets import BaseFormSet
from django.forms.models import BaseModelFormSet
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from activities.tests.factories import CourseFactory
from activities.tests.factories import ExtraNeedFactory
from backend.forms import BillingForm
from backend.forms import ChildSelectForm
from backend.forms import CourseSelectForm
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Bill
from registrations.models import Registration
from registrations.tests.factories import FIXTURES_PATH
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import ExtraInfoFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase
from sportfac.utils import process_request_for_middleware

from ...views.registration_views import RegistrationCreateView
from ...views.registration_views import RegistrationDeleteView
from ...views.registration_views import RegistrationDetailView
from ...views.registration_views import RegistrationListView
from ...views.registration_views import RegistrationsMoveView
from ...views.registration_views import RegistrationUpdateView
from .base import fake_registrations_open_middleware


class RegistrationCreateViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:registration-create")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationCreateView.as_view()
        self.request = self.factory.get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        process_request_for_middleware(self.request, SessionMiddleware)
        self.child = ChildFactory()
        self.course = CourseFactory(age_min=None, age_max=None, schoolyear_min=None, schoolyear_max=None)
        self.registration = Registration()
        self.child_form = ChildSelectForm(instance=self.registration, data={"child": self.child})
        self.child_form.is_valid()
        self.course_form = CourseSelectForm(instance=self.registration, data={"course": self.course})
        self.course_form.is_valid()
        self.billing_form = BillingForm(instance=self.registration, data={"paid": False, "send_confirmation": True})
        self.billing_form.is_valid()
        self.form_list = [self.child_form, self.course_form, self.billing_form]
        self.form_dict = {
            _("Child"): self.child_form,
            _("Course"): self.course_form,
            _("Billing"): self.billing_form,
        }

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def post_registration(self, **data):
        request = self.factory.post(self.url, data={"child": self.child.pk, "course": self.course.pk, **data})
        request.user = self.user
        return self.view(request)

    def test_single_page_shows_all_options(self):
        with override_settings(KEPCHUP_NO_PAYMENT=False):
            response = self.view(self.request).render()
        self.assertContains(response, 'name="child"')
        self.assertContains(response, 'name="course"')
        self.assertContains(response, 'name="paid"')
        self.assertContains(response, 'name="send_confirmation"')
        self.assertNotContains(response, "wizard_goto_step")

    def test_course_fragment_is_filtered_and_does_not_create_registration(self):
        RegistrationFactory(child=self.child, course=self.course)
        request = self.factory.get(self.url, {"courses": "1", "child": self.child.pk})
        request.user = self.user
        response = self.view(request).render()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="course"')
        self.assertNotContains(response, "<form")
        self.assertNotIn(self.course, response.context_data["form"].fields["course"].queryset)
        self.assertEqual(Registration.objects.count(), 1)

    @override_settings(KEPCHUP_NO_PAYMENT=True)
    @mock.patch.object(RegistrationCreateView, "set_message")
    def test_single_post_creates_confirmed_registration_without_bill(self, _message):
        response = self.post_registration()
        self.assertEqual(response.status_code, 302)
        registration = Registration.objects.get(child=self.child, course=self.course)
        self.assertEqual(registration.status, Registration.STATUS.confirmed)
        self.assertEqual(Bill.objects.count(), 0)

    @override_settings(KEPCHUP_NO_PAYMENT=True)
    def test_payment_option_is_hidden_without_payment(self):
        response = self.view(self.request).render()
        self.assertNotContains(response, 'name="paid"')
        self.assertContains(response, 'name="send_confirmation"')

    def test_without_javascript_refresh_only_displays_courses(self):
        response = self.post_registration(refresh_courses="1")
        response.render()
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.course, response.context_data["form"].fields["course"].queryset)
        self.assertFalse(Registration.objects.exists())

    @override_settings(KEPCHUP_LIMIT_BY_SCHOOL_YEAR=False, KEPCHUP_EXPLICIT_SESSION_DATES=False)
    def test_post_rechecks_child_age_instead_of_trusting_course_selection(self):
        self.course = CourseFactory(age_min=8, age_max=None, start_date=date.today())
        self.child.birth_date = date.today()
        self.child.save()
        response = self.post_registration()
        self.assertEqual(response.status_code, 200)
        self.assertIn("course", response.context_data["form"].errors)
        self.assertFalse(Registration.objects.exists())

    def test_fragment_requires_backend_access(self):
        request = self.factory.get(self.url, {"courses": "1", "child": self.child.pk})
        for user in (AnonymousUser(), FamilyUserFactory(is_manager=False)):
            with self.subTest(user=user):
                request.user = user
                self.assertEqual(self.view(request).status_code, 302)

    @override_settings(KEPCHUP_NO_PAYMENT=False)
    @mock.patch.object(RegistrationCreateView, "set_message")
    def test_single_post_creates_registration_and_bill(self, _message):
        with mock.patch.object(Bill, "send_to_accountant"), mock.patch.object(
            Bill, "send_confirmation"
        ) as confirmation:
            response = self.post_registration(paid="on", send_confirmation="on")
        self.assertEqual(response.status_code, 302)
        registration = Registration.objects.get(child=self.child, course=self.course)
        self.assertEqual(registration.status, Registration.STATUS.confirmed)
        self.assertTrue(registration.paid)
        self.assertTrue(registration.bill.is_paid)
        confirmation.assert_called_once()

    def test_duplicate_post_is_rejected_without_new_bill(self):
        RegistrationFactory(child=self.child, course=self.course)
        response = self.post_registration()
        self.assertEqual(response.status_code, 200)
        self.assertIn("course", response.context_data["form"].errors)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(Bill.objects.count(), 0)

    def test_familyless_child_is_rejected(self):
        child = ChildFactory(family=None)
        response = self.post_registration(child=child.pk)
        self.assertEqual(response.status_code, 200)
        self.assertIn("child", response.context_data["form"].errors)
        self.assertFalse(Registration.objects.exists())

    def test_restricted_manager_cannot_register_to_other_activity(self):
        self.user = FamilyUserFactory(is_manager=True, is_restricted_manager=True)
        response = self.post_registration()
        self.assertEqual(response.status_code, 200)
        self.assertIn("course", response.context_data["form"].errors)
        self.assertFalse(Registration.objects.exists())

    @override_settings(KEPCHUP_NO_PAYMENT=True)
    @mock.patch.object(RegistrationCreateView, "set_message")
    def test_done_no_payment(self, _set_message):
        view = RegistrationCreateView()
        self.registration.save()
        view.instance = self.registration
        with mock.patch.object(Registration, "set_confirmed") as mock_set_confirmed:
            response = view.done(self.form_list, self.form_dict)
            mock_set_confirmed.assert_called_once_with(
                send_confirmation=self.billing_form.cleaned_data["send_confirmation"]
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.course.get_backend_url())

    @override_settings(KEPCHUP_NO_PAYMENT=False)
    @mock.patch.object(RegistrationCreateView, "set_message")
    def test_done_creates_bill(self, _set_message):
        view = RegistrationCreateView()
        self.registration.save()
        view.instance = self.registration
        with mock.patch.object(Registration, "set_confirmed") as set_confirmed, mock.patch.object(
            Bill, "send_to_accountant"
        ) as send_to_accountant, mock.patch.object(Bill, "send_confirmation") as send_confirmation:
            response = view.done(self.form_list, self.form_dict)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, self.course.get_backend_url())
            send_to_accountant.assert_called_once()
            send_confirmation.assert_called_once()
            set_confirmed

        self.registration.refresh_from_db()
        self.assertTrue(hasattr(self.registration, "bill"))

    @override_settings(KEPCHUP_NO_PAYMENT=False)
    @mock.patch.object(RegistrationCreateView, "set_message")
    def test_done_sets_bill_status_to_paid(self, _set_message):
        view = RegistrationCreateView()
        self.registration.save()
        view.instance = self.registration
        with mock.patch.object(Registration, "set_confirmed"), mock.patch.object(
            Registration, "get_price", return_value=0
        ), mock.patch.object(Bill, "send_to_accountant"), mock.patch.object(Bill, "send_confirmation"):
            view.done(self.form_list, self.form_dict)

        self.registration.refresh_from_db()
        self.assertTrue(hasattr(self.registration, "bill"))
        bill = self.registration.bill
        self.assertTrue(bill.is_paid)


class RegistrationDeleteViewTests(TenantTestCase):
    def setUp(self):
        self.registration = RegistrationFactory()
        self.data = {"confirm": "True"}
        self.login_url = reverse("profiles:auth_login")
        self.url = self.registration.get_delete_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationDeleteView.as_view()
        self.request = RequestFactory().get(self.url)
        self.request.user = self.user
        fake_registrations_open_middleware(self.request)

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    def test_post_is_302_and_registration_is_canceled(self, _):
        course = self.registration.course
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, course.get_backend_url())
        self.assertEqual(Registration.objects.all_with_deleted().count(), 1)
        registration = Registration.objects.all_with_deleted().first()
        self.assertEqual(registration.status, Registration.STATUS.canceled)


class RegistrationDetailViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.registration = RegistrationFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = self.registration.get_backend_url()
        self.view = RegistrationDetailView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        KEPCHUP_BIB_NUMBERS=True,
        KEPCHUP_REGISTRATION_LEVELS=True,
        KEPCHUP_DISPLAY_CAR_NUMBER=True,
        KEPCHUP_DISPLAY_REGISTRATION_NOTE=True,
        KEPCHUP_EMERGENCY_NUMBER_MANDATORY=True,
        KEPCHUP_LIMIT_BY_SCHOOL_YEAR=True,
        KEPCHUP_USES_ABSENCES=True,
    )
    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    def test_extra_is_displayed_boolean(self):
        extra_need_true = ExtraNeedFactory(type="B")
        ExtraInfoFactory(registration=self.registration, key=extra_need_true, value="1")
        extra_need_false = ExtraNeedFactory(type="B")
        ExtraInfoFactory(registration=self.registration, key=extra_need_false, value="0")
        response = self.view(self.request, pk=self.registration.pk)
        content = response.render().content
        soup = BeautifulSoup(content, "html.parser")
        dt_element = soup.find("dt", string=extra_need_true.question_label)
        self.assertIsNotNone(dt_element, "Question label not found in the rendered HTML!")
        # Check if the next element is a <dd> containing an <i> with class 'icon-ok'
        next_element = dt_element.find_next_sibling()
        if next_element and next_element.name == "dd":
            icon_element = next_element.find("i", class_="icon-ok")
            self.assertIsNotNone(icon_element, "Icon with class 'icon-ok' not found in the subsequent <dd>!")
        else:
            self.fail("<dd> tag not found after the <dt> tag with the question label!")
        dt_element = soup.find("dt", string=extra_need_false.question_label)
        self.assertIsNotNone(dt_element, "Question label not found in the rendered HTML!")
        # Check if the next element is a <dd> containing an <i> with class 'icon-ok'
        next_element = dt_element.find_next_sibling()
        if next_element and next_element.name == "dd":
            icon_element = next_element.find("i", class_="icon-cancel")
            self.assertIsNotNone(icon_element, "Icon with class 'icon-cancel' not found in the subsequent <dd>!")
        else:
            self.fail("<dd> tag not found after the <dt> tag with the question label!")

    def test_extra_is_displayed_image(self):
        extra_need = ExtraNeedFactory(type="IM")
        extra_info = ExtraInfoFactory(registration=self.registration, key=extra_need, value="1")
        image_path = FIXTURES_PATH / "magic_pass.png"
        with open(image_path, "rb") as image:
            file_data = SimpleUploadedFile("magic_pass.png", image.read(), content_type="image/png")
            extra_info.image = file_data
            extra_info.save()
        response = self.view(self.request, pk=self.registration.pk)
        content = response.render().content
        soup = BeautifulSoup(content, "html.parser")
        dt_element = soup.find("dt", string=extra_need.question_label)
        self.assertIsNotNone(dt_element, "Question label not found in the rendered HTML!")
        # Check if the next element is a <dd> containing an <i> with class 'icon-ok'
        next_element = dt_element.find_next_sibling()
        if next_element and next_element.name == "dd":
            icon_element = next_element.find("i", class_="icon-ok")
            self.assertIsNotNone(icon_element, "Icon with class 'icon-ok' not found in the subsequent <dd>!")
        else:
            self.fail("<dd> tag not found after the <dt> tag with the question label!")
        img_element = next_element.find("img")
        self.assertIsNotNone(img_element, "image not found!")
        self.assertEqual(img_element["src"], extra_info.image.url)

    def test_extra_is_displayed_image_empty(self):
        extra_need = ExtraNeedFactory(type="IM")
        ExtraInfoFactory(registration=self.registration, key=extra_need, value="0")
        response = self.view(self.request, pk=self.registration.pk)
        content = response.render().content
        soup = BeautifulSoup(content, "html.parser")
        dt_element = soup.find("dt", string=extra_need.question_label)
        self.assertIsNotNone(dt_element, "Question label not found in the rendered HTML!")
        # Check if the next element is a <dd> containing an <i> with class 'icon-ok'
        next_element = dt_element.find_next_sibling()
        if next_element and next_element.name == "dd":
            icon_element = next_element.find("i", class_="icon-cancel")
            self.assertIsNotNone(icon_element, "Icon with class 'icon-cancel' not found in the subsequent <dd>!")
        else:
            self.fail("<dd> tag not found after the <dt> tag with the question label!")
        img_element = next_element.find("img")
        self.assertIsNone(img_element, "image is present but should not!")


class RegistrationListViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.registration = RegistrationFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:registration-list")
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationListView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)


class RegistrationUpdateViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.registration = RegistrationFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = self.registration.get_update_url()
        self.user = FamilyUserFactory(is_manager=True)
        self.view = RegistrationUpdateView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        self.data = model_to_dict(self.registration)
        self.data["extra_infos-TOTAL_FORMS"] = 0
        self.data["extra_infos-INITIAL_FORMS"] = 0
        self.data["extra_infos-MIN_NUM_FORMS"] = 0
        self.data["extra_infos-MAX_NUM_FORMS"] = 1000

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 200)

    def test_content_is_rendered(self):
        response = self.view(self.request, pk=self.registration.pk)
        # noinspection PyUnresolvedReferences
        content = response.render().content
        self.assertTrue(len(content) > 0)

    @patch("django.contrib.messages.success")
    @patch.object(BaseFormSet, "is_valid", return_value=True)
    @patch.object(BaseModelFormSet, "save")
    def test_post_is_302(self, _, __, ___):
        self.request.method = "POST"
        self.request.POST = self.data
        response = self.view(self.request, pk=self.registration.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("backend:registration-list"))


class RegistrationMoveViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = FamilyUserFactory(is_manager=True)
        self.registration = RegistrationFactory()
        self.login_url = reverse("profiles:auth_login")
        self.url = reverse("backend:registrations-move")
        self.view = RegistrationsMoveView.as_view()
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user

    def test_access_forbidden_for_anonymous_users(self):
        self.request.user = AnonymousUser()
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_access_forbidden_for_non_backend_users(self):
        self.request.user = FamilyUserFactory(is_manager=False)
        response = self.view(self.request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, str(self.login_url + "?next=" + self.url))

    def test_get_is_200(self):
        response = self.view(self.request)
        self.assertEqual(response.status_code, 200)

    def test_initial_course(self):
        self.url = reverse("backend:registrations-move") + f"?course={self.registration.course.pk}"
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        response = self.view(self.request)
        context = response.context_data
        self.assertEqual(context["form"].initial, {"origin_course_id": self.registration.course.pk})

    def test_initial_activity(self):
        self.url = reverse("backend:registrations-move") + f"?activity={self.registration.course.activity.pk}"
        self.request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(self.request)
        self.request.user = self.user
        response = self.view(self.request)
        context = response.context_data
        self.assertEqual(context["form"].initial, {"origin_activity_id": self.registration.course.activity.pk})
