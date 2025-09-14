from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import ButtonHolder
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from backend.forms import ChildWidget
from registrations.models import Child

from .models import WaitingSlot


class WaitingSlotForm(forms.ModelForm):
    child = forms.ModelChoiceField(
        label=_("Child"),
        queryset=Child.objects.exclude(family=None),
        empty_label=None,
        widget=ChildWidget(),
    )

    class Meta:
        model = WaitingSlot
        fields = ["child", "course"]
        widgets = {"course": forms.HiddenInput()}
        error_messages = {
            NON_FIELD_ERRORS: {"unique_together": _("This child is already on the waiting list for this course.")}
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.form_action = reverse(
            "backend:waiting_slot-add", kwargs={"course_id": self.initial.get("course").id}
        )
        self.helper.layout = Layout(
            "course",
            "child",
            Submit("add", _("Add to waiting list"), css_class="btn btn-success"),
        )


class WaitingSlotTransformForm(forms.ModelForm):
    send_confirmation = forms.BooleanField(required=False, initial=True, label=_("Send confirmation email"))

    class Meta:
        model = WaitingSlot
        fields = ["send_confirmation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            "send_confirmation",
            ButtonHolder(
                Submit("add", _("Add to participants"), css_class="btn btn-success"),
                HTML(
                    '<a href="%s" class="btn btn-default">%s</a>'
                    % (self.instance.course.get_backend_url(), _("Cancel"))
                ),
                css_class="form-group",
            ),
        )
