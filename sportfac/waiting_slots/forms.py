from __future__ import absolute_import

from django import forms
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Layout, Submit

from .models import WaitingSlot


class WaitingSlotTransformForm(forms.ModelForm):
    send_confirmation = forms.BooleanField(
        required=False, initial=True, label=_("Send confirmation email")
    )

    class Meta:
        model = WaitingSlot
        fields = ["send_confirmation"]

    def __init__(self, *args, **kwargs):
        super(WaitingSlotTransformForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()

        self.helper.layout = Layout(
            "send_confirmation",
            ButtonHolder(
                Submit("add", _("Add to participants"), css_class="btn btn-success"),
                HTML(
                    '<a href="%s" class="btn btn-default">%s</a>'
                    % (self.instance.course.get_backend_url(), _("Cancel"))
                ),
            ),
        )
