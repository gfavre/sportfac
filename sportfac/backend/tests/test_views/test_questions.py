from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from activities.models import ExtraNeed
from activities.tests.factories import CourseFactory
from backend.question_forms import QuestionForm
from backend.views.question_views import QuestionDeleteView
from backend.views.question_views import QuestionEditView
from backend.views.question_views import QuestionListView
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ExtraInfo
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


class QuestionManagementTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.course = CourseFactory()
        self.question = ExtraNeed.objects.create(
            question_label="Magic Pass ?", type="B", choices=[], price_modifier=[0, -40]
        )
        self.question.courses.add(self.course)

    def request(self, url, data=None, user=None):
        request = RequestFactory().get(url) if data is None else RequestFactory().post(url, data)
        request.user = user if user is not None else self.manager
        fake_registrations_open_middleware(request)
        return request

    def data(self, **kwargs):
        data = {
            "question_label": "Magic Pass ?",
            "type": "B",
            "mandatory": "on",
            "no_price": "0",
            "yes_price": "-40",
            "default": "",
            "extra_info": "",
            "courses": [self.course.pk],
            "answers-TOTAL_FORMS": "0",
            "answers-INITIAL_FORMS": "0",
        }
        data.update(kwargs)
        return data

    def answer(self):
        return ExtraInfo.objects.create(
            registration=RegistrationFactory(course=self.course), key=self.question, value="1"
        )

    def test_pages_and_permissions(self):
        cases = [
            ("question-list", QuestionListView.as_view(), {}),
            ("question-create", QuestionEditView.as_view(), {}),
            ("question-update", QuestionEditView.as_view(), {"pk": self.question.pk}),
            ("question-duplicate", QuestionEditView.as_view(duplicate=True), {"pk": self.question.pk}),
            ("question-delete", QuestionDeleteView.as_view(), {"pk": self.question.pk}),
        ]
        for name, view, kwargs in cases:
            url = reverse("backend:" + name, kwargs=kwargs)
            for user in (self.manager, FamilyUserFactory(is_staff=True)):
                response = view(self.request(url, user=user), **kwargs)
                self.assertEqual(response.status_code, 200)
                response.render()
            for user in (AnonymousUser(), FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
                for data in (None, self.data()):
                    self.assertEqual(view(self.request(url, data, user), **kwargs).status_code, 302)

    @patch("backend.views.question_views.messages.success")
    def test_create_update_and_unassign_preserve_answers(self, _):
        url = reverse("backend:question-create")
        response = QuestionEditView.as_view()(self.request(url, self.data()))
        self.assertEqual(response.status_code, 302)
        created = ExtraNeed.objects.exclude(pk=self.question.pk).get()
        self.assertEqual(created.price_dict, {"0": 0, "1": -40})
        self.assertEqual(list(created.courses.all()), [self.course])
        answer = self.answer()
        response = QuestionEditView.as_view()(
            self.request(url, self.data(question_label="Nouveau libellé", courses=[])), pk=self.question.pk
        )
        self.assertEqual(response.status_code, 302)
        self.question.refresh_from_db()
        self.assertEqual(self.question.question_label, "Nouveau libellé")
        self.assertFalse(self.question.courses.exists())
        answer.refresh_from_db()
        self.assertEqual(answer.price_modifier, -40)

    @patch("backend.views.question_views.messages.success")
    def test_duplicate_preserves_original_and_does_not_assign_courses(self, _):
        self.answer()
        response = QuestionEditView.as_view(duplicate=True)(
            self.request("/", self.data(yes_price="-80", courses=[])), pk=self.question.pk
        )
        self.assertEqual(response.status_code, 302)
        copied = ExtraNeed.objects.exclude(pk=self.question.pk).get()
        self.assertEqual(copied.price_dict["1"], -80)
        self.assertFalse(copied.courses.exists())
        self.question.refresh_from_db()
        self.assertEqual(self.question.price_dict["1"], -40)
        self.assertTrue(self.question.courses.filter(pk=self.course.pk).exists())

    @patch("backend.views.question_views.messages.success")
    def test_existing_answers_require_confirmation_for_type_and_price_changes(self, _):
        answer = self.answer()
        for changes in ({"type": "C"}, {"yes_price": "-80"}):
            self.question.type = "B"
            self.question.price_modifier = [0, -40]
            self.question.save()
            response = QuestionEditView.as_view()(self.request("/", self.data(**changes)), pk=self.question.pk)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.template_name, "backend/questions/confirm.html")
            self.assertContains(response, 'name="confirm_changes"')
            self.question.refresh_from_db()
            self.assertEqual(self.question.type, "B")
            self.assertEqual(self.question.price_modifier, [0, -40])
            response = QuestionEditView.as_view()(
                self.request("/", self.data(confirm_changes="on", **changes)), pk=self.question.pk
            )
            self.assertEqual(response.status_code, 302)
            self.question.refresh_from_db()
            self.assertEqual(self.question.type, changes.get("type", "B"))
            self.assertEqual(self.question.price_modifier, [] if changes.get("type") == "C" else [0, -80])
            answer.refresh_from_db()
            self.assertEqual(answer.value, "1")

    @patch("backend.views.question_views.messages.success")
    @patch("backend.views.question_views.messages.error")
    def test_delete_protects_answers_and_get_never_deletes(self, error, success):
        view = QuestionDeleteView.as_view()
        self.assertEqual(view(self.request("/"), pk=self.question.pk).status_code, 200)
        self.assertTrue(ExtraNeed.objects.filter(pk=self.question.pk).exists())
        answer = self.answer()
        view(self.request("/", {}), pk=self.question.pk)
        self.assertTrue(ExtraInfo.objects.filter(pk=answer.pk).exists())
        error.assert_called_once()
        unused = ExtraNeed.objects.create(question_label="Unused", type="C", choices=[])
        view(self.request("/", {}), pk=unused.pk)
        self.assertFalse(ExtraNeed.objects.filter(pk=unused.pk).exists())
        success.assert_called_once()

    def choice_data(self, **kwargs):
        return self.data(
            **{
                "type": "C",
                "answers-TOTAL_FORMS": "2",
                "answers-0-value": "Petit",
                "answers-0-price": "-20",
                "answers-1-value": "Grand",
                "answers-1-price": "30",
                **kwargs,
            }
        )

    def test_choice_validation_and_persistence(self):
        form = QuestionForm(self.choice_data())
        self.assertTrue(form.is_valid(), form.errors)
        question = form.save()
        self.assertEqual(question.price_dict, {"Petit": -20, "Grand": 30})
        for data in (
            self.choice_data(**{"answers-1-value": "Petit"}),
            self.choice_data(type="I"),
            self.choice_data(default="Inconnu"),
            self.choice_data(**{"answers-0-price": "1.5"}),
            self.choice_data(**{"answers-TOTAL_FORMS": "invalid"}),
        ):
            self.assertFalse(QuestionForm(data).is_valid())
        question.type = "I"
        question.save()
        form = QuestionForm(self.choice_data(type="I", **{"answers-0-value": "10", "answers-1-value": "20"}))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().choices, ["10", "20"])

    def test_used_choices_require_confirmation_to_remove_or_rename(self):
        self.question.type = "C"
        self.question.choices = ["Petit", "Grand"]
        self.question.price_modifier = [-20, 30]
        self.question.save()
        self.answer()
        for changes in ({"answers-0-DELETE": "on"}, {"answers-0-value": "Autre"}):
            form = QuestionForm(self.choice_data(**changes), instance=ExtraNeed.objects.get(pk=self.question.pk))
            self.assertFalse(form.is_valid())
            self.assertIn("confirm_changes", form.errors)
            confirmed = QuestionForm(
                self.choice_data(confirm_changes="on", **changes),
                instance=ExtraNeed.objects.get(pk=self.question.pk),
            )
            self.assertTrue(confirmed.is_valid(), confirmed.errors)
        form = QuestionForm(self.choice_data(), instance=ExtraNeed.objects.get(pk=self.question.pk))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.requires_confirmation)

    def test_empty_choices_and_boolean_defaults(self):
        for kind in ("C", "I", "IM"):
            form = QuestionForm(self.data(type=kind))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.save().choices, [])
        self.assertFalse(QuestionForm(self.data(default="yes")).is_valid())

    def test_legacy_boolean_choices_survive_confirmed_price_change(self):
        self.question.choices = ["NON", "OUI"]
        self.question.save()
        self.answer()
        form = QuestionForm(self.data(), instance=self.question)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.requires_confirmation)
        form = QuestionForm(
            self.data(yes_price="-80", confirm_changes="on"),
            instance=ExtraNeed.objects.get(pk=self.question.pk),
        )
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.choices, ["NON", "OUI"])
        self.assertEqual(saved.price_modifier, [0, -80])

    def test_confirmation_back_keeps_edits_without_saving(self):
        self.answer()
        data = self.data(yes_price="-80", question_label="New wording", courses=[])
        response = QuestionEditView.as_view()(self.request("/", data), pk=self.question.pk)
        self.assertEqual(response.template_name, "backend/questions/confirm.html")
        self.assertIn(("question_label", "New wording"), response.context_data["submitted_fields"])
        data["action"] = "edit"
        response = QuestionEditView.as_view()(self.request("/", data), pk=self.question.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["form"]["yes_price"].value(), "-80")
        self.assertEqual(response.context_data["form"]["question_label"].value(), "New wording")
        self.assertFalse(response.context_data["form"].errors)
        self.question.refresh_from_db()
        self.assertEqual(self.question.question_label, "Magic Pass ?")
        self.assertEqual(self.question.price_modifier, [0, -40])
        self.assertTrue(self.question.courses.filter(pk=self.course.pk).exists())

    def test_reordered_answers_keep_their_prices(self):
        form = QuestionForm(
            self.choice_data(
                **{
                    "answers-0-value": "Grand",
                    "answers-0-price": "30",
                    "answers-1-value": "Petit",
                    "answers-1-price": "-20",
                }
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        question = form.save()
        question.refresh_from_db()
        self.assertEqual(question.choices, ["Grand", "Petit"])
        self.assertEqual(question.price_modifier, [30, -20])
        self.assertEqual(question.price_dict, {"Grand": 30, "Petit": -20})
