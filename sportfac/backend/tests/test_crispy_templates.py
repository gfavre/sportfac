from copy import deepcopy

from crispy_forms.utils import render_crispy_form
from django import forms
from django.conf import settings
from django.test import SimpleTestCase


class CrispyBootstrapTemplatesTest(SimpleTestCase):
    def test_bootstrap3_form_renders(self):
        class ExampleForm(forms.Form):
            name = forms.CharField(label="Name")

        templates = deepcopy(settings.TEMPLATES)
        # Exercise the installed template pack without the database template loader.
        templates[0]["OPTIONS"]["loaders"] = [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ]
        with self.settings(TEMPLATES=templates):
            html = render_crispy_form(ExampleForm())

        self.assertIn('name="name"', html)
        self.assertIn("form-control", html)
