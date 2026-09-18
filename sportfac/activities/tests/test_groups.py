import ast
from pathlib import Path

from django.contrib.admin.sites import AdminSite
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.test import override_settings

from activities.admin import CoursesAdmin
from activities.forms import CourseForm
from activities.forms import ExplicitDatesCourseForm
from activities.models import Course
from activities.tests.factories import CourseFactory
from api.serializers import RegistrationDatatableSerializer
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase


class LocalCourseGroupSettingsTests(SimpleTestCase):
    def test_local_activation_is_executable_not_inside_example_text(self):
        path = Path(__file__).parents[2] / "sportfac" / "settings" / "local.py"
        assignments = [
            node.value
            for node in ast.parse(path.read_text()).body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "KEPCHUP_COURSE_GROUPS" for target in node.targets)
        ]
        self.assertTrue(assignments, "The flag must be an executable assignment, not text inside local_settings.")
        self.assertIs(ast.literal_eval(assignments[-1]), True)


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False, KEPCHUP_COURSE_GROUPS=True)
class CourseGroupTests(TenantTestCase):
    @override_settings(KEPCHUP_COURSE_GROUPS=True)
    def test_group_is_optional_and_editable_in_both_course_forms(self):
        course = CourseFactory()
        self.assertEqual(course.group_name, "")
        for form_class in (CourseForm, ExplicitDatesCourseForm):
            form = form_class(instance=course)
            self.assertIn("group_name", form.fields)
            self.assertFalse(form.fields["group_name"].required)
        self.assertEqual(render_to_string("activities/includes/course-group.html", {"course": course}).strip(), "")

    @override_settings(KEPCHUP_COURSE_GROUPS=True)
    def test_group_is_shared_by_registrations_and_updates_without_changing_children(self):
        course = CourseFactory(group_name="3")
        registrations = RegistrationFactory.create_batch(2, course=course)
        second_course = CourseFactory(group_name="Bleu")
        other_registration = RegistrationFactory(child=registrations[0].child, course=second_course)
        for registration in registrations:
            self.assertEqual(RegistrationDatatableSerializer(registration).data["group_name"], "3")
        course.group_name = "4"
        course.save(update_fields=["group_name"])
        for registration in registrations:
            registration.refresh_from_db()
            self.assertEqual(RegistrationDatatableSerializer(registration).data["group_name"], "4")
        self.assertEqual(RegistrationDatatableSerializer(other_registration).data["group_name"], "Bleu")
        course.group_name = ""
        course.save(update_fields=["group_name"])
        registrations[0].refresh_from_db()
        self.assertEqual(RegistrationDatatableSerializer(registrations[0]).data["group_name"], "")

    def test_group_label_is_escaped(self):
        course = CourseFactory(group_name="<script>danger</script>")
        html = render_to_string("activities/includes/course-group.html", {"course": course, "COURSE_GROUPS": True})
        self.assertIn("&lt;script&gt;danger&lt;/script&gt;", html)
        self.assertNotIn("<script>", html)

    @override_settings(KEPCHUP_COURSE_GROUPS=False)
    def test_disabled_feature_hides_forms_api_and_templates_without_erasing_group(self):
        course = CourseFactory(group_name="Bleu")
        for form_class in (CourseForm, ExplicitDatesCourseForm):
            form = form_class(data={"group_name": "Rouge"}, instance=course)
            self.assertNotIn("group_name", form.fields)
        registration = RegistrationFactory(course=course)
        self.assertNotIn("group_name", RegistrationDatatableSerializer(registration).data)
        self.assertEqual(
            render_to_string(
                "activities/includes/course-group.html", {"course": course, "COURSE_GROUPS": False}
            ).strip(),
            "",
        )
        admin = CoursesAdmin(Course, AdminSite())
        self.assertIn("group_name", admin.get_exclude(None))
        self.assertNotIn("group_name", admin.get_list_display(None))
        course.refresh_from_db()
        self.assertEqual(course.group_name, "Bleu")

    @override_settings(KEPCHUP_COURSE_GROUPS=True)
    def test_enabled_feature_exposes_admin_fields(self):
        admin = CoursesAdmin(Course, AdminSite())
        self.assertNotIn("group_name", admin.get_exclude(None))
        self.assertIn("group_name", admin.get_list_display(None))
