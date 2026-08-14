import tempfile
import zipfile
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from activities.tests.factories import CourseFactory
from activities.tests.factories import CoursesInstructorsFactory
from profiles.tests.factories import FamilyUserFactory
from sportfac.utils import TenantTestCase

from ...views.course_views import CourseDecompteDownloadView
from .base import fake_registrations_open_middleware


def _fake_decompte(course, instructor):
    f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    f.write(b"%PDF fake")
    f.flush()
    return f.name


class CourseDecompteDownloadViewTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.course = CourseFactory()
        self.instructor = FamilyUserFactory()
        CoursesInstructorsFactory(course=self.course, instructor=self.instructor)
        self.url = reverse("backend:course-decompte-download", kwargs={"course": self.course.pk})
        self.view = CourseDecompteDownloadView.as_view()

    def _get(self, user=None):
        request = RequestFactory().get(self.url)
        fake_registrations_open_middleware(request)
        request.user = user or self.manager
        return self.view(request, course=self.course.pk)

    def test_anonymous_is_redirected(self):
        response = self._get(user=AnonymousUser())
        self.assertEqual(response.status_code, 302)

    def test_non_manager_is_redirected(self):
        response = self._get(user=FamilyUserFactory(is_manager=False))
        self.assertEqual(response.status_code, 302)

    @patch("mailer.pdfutils.get_ssf_decompte_heures", side_effect=_fake_decompte)
    def test_single_instructor_returns_pdf(self, mock_decompte):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".pdf", response["Content-Disposition"])
        mock_decompte.assert_called_once_with(self.course, self.instructor)

    @patch("mailer.pdfutils.get_ssf_decompte_heures", side_effect=_fake_decompte)
    def test_multiple_instructors_returns_zip(self, mock_decompte):
        second = FamilyUserFactory()
        CoursesInstructorsFactory(course=self.course, instructor=second)
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn(".zip", response["Content-Disposition"])
        self.assertEqual(mock_decompte.call_count, 2)

    @patch("mailer.pdfutils.get_ssf_decompte_heures", side_effect=_fake_decompte)
    def test_zip_contains_one_pdf_per_instructor(self, _mock):
        second = FamilyUserFactory()
        CoursesInstructorsFactory(course=self.course, instructor=second)
        response = self._get()
        import io

        zf = zipfile.ZipFile(io.BytesIO(response.content))
        self.assertEqual(len(zf.namelist()), 2)
        for name in zf.namelist():
            self.assertTrue(name.endswith(".pdf"))
