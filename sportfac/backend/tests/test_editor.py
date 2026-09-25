from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from activities.models import Activity
from activities.models import Course
from activities.tests.factories import CourseFactory
from backend.forms import FlatPageForm
from mailer.models import GenericEmail
from profiles.tests.factories import FamilyUserFactory
from sportfac.richtext import RichTextField
from sportfac.richtext import RichTextWidget
from sportfac.utils import TenantTestCase
from wizard.models import WizardStep


class EditorTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.media = Path(directory.name)
        config = override_settings(MEDIA_ROOT=directory.name, MEDIA_URL="/media/")
        config.enable()
        self.addCleanup(config.disable)
        self.manager = FamilyUserFactory(is_manager=True)
        self.upload_url = reverse("editor-upload")
        self.browse_url = reverse("editor-browse")

    def picture(self):
        output = BytesIO()
        Image.new("RGB", (4, 4), "red").save(output, format="PNG")
        return SimpleUploadedFile("image.png", output.getvalue(), content_type="image/png")

    def test_upload_browse_and_existing_images(self):
        self.client.force_login(self.manager)
        response = self.client.post(self.upload_url, {"files[0]": self.picture()})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["isImages"][0])
        self.assertTrue(data["files"][0].startswith("http://"))
        saved = list(self.media.rglob("*.png"))
        self.assertEqual(len(saved), 1)
        Image.open(saved[0]).verify()
        old = self.media / "uploads" / "old"
        old.mkdir()
        (old / "existing.png").write_bytes(self.picture().read())
        (old / "private.txt").write_text("Not an image")
        response = self.client.get(self.browse_url, {"action": "folders"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("old", response.json()["data"]["sources"][0]["folders"])
        response = self.client.get(self.browse_url, {"action": "files", "path": "old/"})
        self.assertEqual(response.status_code, 200)
        files = response.json()["data"]["sources"][0]["files"]
        self.assertEqual([file["name"] for file in files], ["existing.png"])
        self.assertTrue(files[0]["file"].endswith("/media/uploads/old/existing.png"))

    def test_roles_and_methods(self):
        instructor = FamilyUserFactory()
        CourseFactory(instructors=[instructor])
        for user in (None, FamilyUserFactory(), instructor):
            if user:
                self.client.force_login(user)
            else:
                self.client.logout()
            self.assertEqual(self.client.get(self.browse_url).status_code, 302)
            self.assertEqual(self.client.post(self.upload_url, {"files[0]": self.picture()}).status_code, 302)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.upload_url).status_code, 405)
        self.assertEqual(self.client.post(self.browse_url).status_code, 405)

    def test_invalid_upload_and_traversal_are_rejected(self):
        self.client.force_login(self.manager)
        bad = SimpleUploadedFile("evil.png", b"<script>bad()</script>", content_type="image/png")
        response = self.client.post(self.upload_url, {"files[0]": self.picture(), "files[1]": bad})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(self.media.rglob("*.png")), [])
        svg = SimpleUploadedFile("image.svg", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.assertEqual(self.client.post(self.upload_url, {"files[0]": svg}).status_code, 400)
        for path in ("../", "old/../../", "..\\"):
            self.assertEqual(self.client.get(self.browse_url, {"path": path}).status_code, 400)
        self.assertEqual(self.client.get(self.browse_url, {"action": "fileRemove"}).status_code, 403)

    def test_upload_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.manager)
        self.assertEqual(client.post(self.upload_url, {"files[0]": self.picture()}).status_code, 403)

    def test_all_rich_fields_use_jodit_without_changing_storage(self):
        for model, fields in (
            (Activity, ["description", "informations"]),
            (Course, ["comments"]),
            (WizardStep, ["description"]),
            (GenericEmail, ["help_text"]),
        ):
            for name in fields:
                field = model._meta.get_field(name)
                self.assertIsInstance(field, RichTextField)
                self.assertIsInstance(field.formfield().widget, RichTextWidget)
                self.assertEqual(field.deconstruct()[1], "django.db.models.TextField")
        self.assertIsInstance(FlatPageForm().fields["content"].widget, RichTextWidget)
        html = str(RichTextWidget().render("body", '<p class="alert alert-info">Déjà enregistré</p>'))
        self.assertIn("data-richtext", html)
        self.assertIn("data-upload-url", html)
        self.assertIn("alert alert-info", html)
        self.assertIn("Déjà enregistré", html)
