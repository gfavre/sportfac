import datetime
import tempfile
from unittest.mock import patch

from django.test import override_settings

from absences.tests.factories import AbsenceFactory
from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase

from ..pdfutils import get_ssf_decompte_heures


def _fake_fill_form(pdf_path, datas, flatten):
    f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    f.write(b"%PDF fake")
    f.flush()
    return f.name


class GetSSFDecompteHeuresTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.instructor = FamilyUserFactory(
            birth_date=datetime.date(1985, 6, 15),
            gender="m",
            is_mep=False,
            is_teacher=False,
        )
        self.course = CourseFactory(
            start_date=datetime.date(2024, 9, 1),
            end_date=datetime.date(2024, 12, 15),
            instructors=[self.instructor],
        )

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    def test_returns_a_file_path(self, _mock):
        result = get_ssf_decompte_heures(self.course, self.instructor)
        self.assertIsNotNone(result)

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    @override_settings(KEPCHUP_DECOMPTE_SHOW_GROUP_NUMBER=True)
    def test_group_number_filled_when_setting_is_true(self, mock_fill):
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["groupe n°"], self.course.number)

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    @override_settings(KEPCHUP_DECOMPTE_SHOW_GROUP_NUMBER=False)
    def test_group_number_empty_when_setting_is_false(self, mock_fill):
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["groupe n°"], "")

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    def test_establishment_uses_preference_when_set(self, mock_fill):
        from dynamic_preferences.registries import global_preferences_registry

        prefs = global_preferences_registry.manager()
        prefs["site__DECOMPTE_ESTABLISHMENT"] = "EPS la Tour-de-Peilz"
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["Escol"], "EPS la Tour-de-Peilz")
        prefs["site__DECOMPTE_ESTABLISHMENT"] = ""

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    def test_establishment_falls_back_to_school_name(self, mock_fill):
        from dynamic_preferences.registries import global_preferences_registry

        prefs = global_preferences_registry.manager()
        prefs["site__DECOMPTE_ESTABLISHMENT"] = ""
        school_name = prefs["email__SCHOOL_NAME"]
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["Escol"], school_name)

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    @override_settings(KEPCHUP_DECOMPTE_ONLY_VALIDATED_SESSIONS=True)
    def test_only_validated_sessions_included(self, mock_fill):
        validated = AbsenceFactory(session__course=self.course).session
        validated.instructor = self.instructor
        validated.save()
        AbsenceFactory(session__course=self.course)  # unvalidated, no instructor
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertIn("date_1", fields)
        self.assertNotIn("date_2", fields)

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    @override_settings(KEPCHUP_DECOMPTE_ONLY_VALIDATED_SESSIONS=False)
    def test_all_sessions_included_when_setting_is_false(self, mock_fill):
        AbsenceFactory(session__course=self.course)
        AbsenceFactory(session__course=self.course)
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertIn("date_1", fields)
        self.assertIn("date_2", fields)

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    def test_mep_checkbox(self, mock_fill):
        self.instructor.is_mep = True
        self.instructor.is_teacher = False
        self.instructor.save()
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["MEP"], "Yes")
        self.assertEqual(fields["Instituteur"], "Off")
        self.assertEqual(fields["JS"], "Off")

    @patch("pypdftk.fill_form", side_effect=_fake_fill_form)
    def test_js_checkbox_when_neither_mep_nor_teacher(self, mock_fill):
        self.instructor.is_mep = False
        self.instructor.is_teacher = False
        self.instructor.save()
        get_ssf_decompte_heures(self.course, self.instructor)
        fields = mock_fill.call_args[1]["datas"]
        self.assertEqual(fields["JS"], "Yes")
        self.assertEqual(fields["MEP"], "Off")
        self.assertEqual(fields["Instituteur"], "Off")
