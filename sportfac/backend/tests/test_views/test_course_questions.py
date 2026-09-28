from unittest.mock import patch

from bs4 import BeautifulSoup
from django.forms.models import model_to_dict
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse

from activities.forms import CourseQuestionsField
from activities.models import Course
from activities.models import ExtraNeed
from activities.tests.factories import CourseFactory
from backend.views.course_views import CourseCreateView
from backend.views.course_views import CourseUpdateView
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ExtraInfo
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


@override_settings(KEPCHUP_NO_EXTRAS=False)
class CourseQuestionsTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.course = CourseFactory(instructors=[self.manager])
        self.questions = [
            ExtraNeed.objects.create(question_label="Magic Pass ?", type="B", price_modifier=[0, discount])
            for discount in (-40, -80)
        ]
        self.course.extra.add(self.questions[0])

    def request(self, url):
        request = RequestFactory().get(url)
        request.user = self.manager
        fake_registrations_open_middleware(request)
        return request

    def test_both_forms_render_distinct_checkboxes_and_existing_selection(self):
        for explicit in (False, True):
            with self.subTest(explicit=explicit), override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=explicit):
                for editing in (False, True):
                    url = self.course.get_update_url() if editing else reverse("backend:course-create")
                    view = CourseUpdateView if editing else CourseCreateView
                    response = view.as_view()(self.request(url), **({"course": self.course.pk} if editing else {}))
                    self.assertEqual(response.status_code, 200)
                    soup = BeautifulSoup(response.render().content, "html.parser")
                    section = soup.select_one("fieldset.course-questions")
                    self.assertIsNotNone(section)
                    self.assertTrue(section.select_one("legend").get_text(strip=True))
                    self.assertEqual(len(section.select('input[name="extra"]')), 2)
                    self.assertNotIn("+0 CHF", section.get_text())
                    for field, sibling in (
                        ("number", "activity"),
                        ("instructors", "place"),
                        ("visible", "allow_new_participants"),
                    ):
                        group = soup.select_one(f'[name="{field}"]').find_parent("fieldset")
                        self.assertIsNotNone(group.select_one(f'[name="{sibling}"]'))
                    self.assertIsNone(
                        soup.select_one('[name="visible"]').find_parent("fieldset").select_one('[name="uptodate"]')
                    )
                    choices = soup.select('input[type="checkbox"][name="extra"]')
                    self.assertEqual({c["value"] for c in choices}, {str(q.pk) for q in self.questions})
                    self.assertEqual(
                        {c["value"] for c in choices if c.has_attr("checked")},
                        {str(self.questions[0].pk)} if editing else set(),
                    )
                    for discount in ("-40 CHF", "-80 CHF"):
                        self.assertIn(discount, soup.get_text())

    @override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
    @patch("django.contrib.messages.success")
    def test_create_and_update_save_selection_without_changing_previous_answers(self, _):
        registration = RegistrationFactory(course=self.course)
        answer = ExtraInfo.objects.create(registration=registration, key=self.questions[0], value="1")
        data = model_to_dict(self.course)
        data["instructors"] = [str(self.manager.pk)]
        data["extra"] = [str(self.questions[1].pk)]
        request = self.request(self.course.get_update_url())
        request.method = "POST"
        request.POST = data
        response = CourseUpdateView.as_view()(request, course=self.course.pk)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(self.course.extra.all()), [self.questions[1]])
        answer.refresh_from_db()
        self.assertEqual(answer.value, "1")
        data["number"] = "new-question-course"
        data.pop("id")
        request = self.request(reverse("backend:course-create"))
        request.method = "POST"
        request.POST = data
        response = CourseCreateView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        created = Course.objects.get(number="new-question-course")
        self.assertEqual(list(created.extra.all()), [self.questions[1]])
        data["extra"] = []
        request = self.request(self.course.get_update_url())
        request.method = "POST"
        data["number"] = self.course.number
        request.POST = data
        self.assertEqual(CourseUpdateView.as_view()(request, course=self.course.pk).status_code, 302)
        self.assertFalse(self.course.extra.exists())
        self.assertTrue(ExtraInfo.objects.filter(pk=answer.pk).exists())

    def test_labels_escape_content_and_describe_choice_prices_and_optional_questions(self):
        field = CourseQuestionsField(queryset=ExtraNeed.objects.all())
        question = ExtraNeed(
            question_label="<script>alert(1)</script>",
            type="C",
            choices=["Petit", "Grand"],
            price_modifier=[-20, 30],
            mandatory=False,
        )
        label = field.label_from_instance(question)
        self.assertNotIn("<script>", label)
        self.assertIn("Petit : -20 CHF", label)
        self.assertIn("Grand : +30 CHF", label)
        question.choices = None
        question.price_modifier = None
        self.assertIn("Sans modification de prix", field.label_from_instance(question))
