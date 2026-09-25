"""Project-owned rich text field: stored as text, edited with local Jodit assets."""
from django import forms
from django.db import models
from django.templatetags.static import static
from django.urls import reverse


class RichTextWidget(forms.Textarea):
    def __init__(self, attrs=None, toggle_selector=None):
        self.toggle_selector = toggle_selector
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_attrs = context["widget"]["attrs"]
        widget_attrs.update(
            {
                "data-richtext": "1",
                "data-upload-url": reverse("editor-upload"),
                "data-browse-url": reverse("editor-browse"),
            }
        )
        if self.toggle_selector:
            widget_attrs["data-html-toggle"] = self.toggle_selector
        return context

    @property
    def media(self):
        # Append versions after storage resolves the path, otherwise '?' is URL-encoded.
        return forms.Media(
            css={"all": (static("backend/vendor/jodit/jodit.min.css") + "?v=4.15.14",)},
            js=(
                static("backend/vendor/jodit/jodit.min.js") + "?v=4.15.14",
                static("backend/js/generic-email.js") + "?v=3",
            ),
        )


class RichTextField(models.TextField):
    def formfield(self, **kwargs):
        kwargs["widget"] = RichTextWidget
        return super().formfield(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # The editor is a form concern, not a database type or migration dependency.
        return name, "django.db.models.TextField", args, kwargs
