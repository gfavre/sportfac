from django import forms
from django import forms as django_forms
from django.utils.translation import gettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit
from multiupload.fields import MultiFileField

from mailer.models import GenericEmail, MailArchive


class MailForm(forms.Form):
    subject = forms.CharField(label=_("Subject"), max_length=255)
    message = forms.CharField(label=_("Message"), widget=forms.Textarea)
    attachments = MultiFileField(label=_("Attachments"), min_num=0, max_file_size=1024 * 1024 * 5, required=False)
    send_copy = forms.BooleanField(label=_("Send me a copy"), initial=True, required=False)

    def __init__(self, *args, **kwargs):
        self.archive: MailArchive = kwargs.pop("archive", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "subject",
            "message",
            "attachments",
            "send_copy",
        )
        self.attachment_pairs = []

        # For each existing attachment, add a checkbox
        if self.archive and self.archive.attachments.exists():
            for att in self.archive.attachments.all():
                field_name = f"delete_attachment_{att.pk}"
                self.fields[field_name] = forms.BooleanField(label=_("Remove ?"), required=False)
                # Create a BoundField for that checkbox
                bound_field = self[field_name]
                # Store them together in a list
                self.attachment_pairs.append((att, bound_field))


class CopiesForm(forms.Form):
    send_copy = forms.BooleanField(label=_("Send me a copy"), initial=True, required=False)
    copy_all_admins = forms.BooleanField(label=_("Send a copy to all other administrators"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "send_copy",
            "copy_all_admins",
        )


class InstructorCopiesForm(MailForm):
    copy_all_instructors = forms.BooleanField(
        label=_("Send a copy to all other instructors"), initial=False, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "subject",
            "message",
            "attachments",
            "send_copy",
            "copy_all_instructors",
        )


class CourseMailForm(MailForm):
    copy_all_instructors = forms.BooleanField(
        label=_("Send a copy to all other instructors"), initial=True, required=False
    )
    copy_all_admins = forms.BooleanField(
        label=_("Send a copy to administrators"), initial=True, required=False, disabled=True
    )

    def __init__(self, *args, enable_copy_all_admins=False, **kwargs):
        super().__init__(*args, **kwargs)
        if enable_copy_all_admins:
            self.fields["copy_all_admins"].disabled = False
            self.fields["copy_all_admins"].initial = False
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "subject",
            "message",
            "attachments",
            "send_copy",
            "copy_all_instructors",
            "copy_all_admins",
        )


class AdminMailForm(MailForm):
    copy_all_admins = forms.BooleanField(
        label=_("Send a copy to all other administrators"), initial=False, required=False
    )


class PreviewForm(forms.Form):
    pass


class GenericEmailForm(django_forms.ModelForm):
    subject_text = forms.CharField(label=_("Subject"), max_length=255)
    body_text = forms.CharField(label=_("Message"), widget=django_forms.Textarea(attrs={"rows": 10}))

    class Meta:
        model = GenericEmail
        fields = ("subject_text", "body_text")

    def cleanup_tmpl(self, body):
        skip = False
        cleaned = []
        for line in body.splitlines():
            if skip:
                cleaned.append(line)
            else:
                if not line.strip() or line.startswith("{% load "):
                    continue
                skip = True
                cleaned.append(line)
        return "\n".join(cleaned)

    def get_tmpl_heading(self, body):
        heading = []
        for line in body.splitlines():
            if not line or line.startswith("{% load "):
                heading.append(line)
                continue
            break
        return "\n".join(heading)

    def get_initial_for_field(self, field, field_name):
        if field_name == "subject_text":
            return self.instance and self.cleanup_tmpl(self.instance.subject_template.content) or ""
        if field_name == "body_text":
            return self.instance and self.cleanup_tmpl(self.instance.body_template.content) or ""
        return super().get_initial_for_field(field, field_name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.layout = Layout(
            "subject_text",
            "body_text",
            Div(
                Div(Submit("save", _("Update email")), css_class="col-sm-10 col-sm-offset-2"),
                css_class="form-group",
            ),
        )
