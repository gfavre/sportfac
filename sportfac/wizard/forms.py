from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from .models import WizardStep


class WizardStepForm(ModelForm):
    class Meta:
        model = WizardStep
        fields = ["title", "subtitle", "lead", "link_display", "description", "slug"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.layout = Layout(
            "title",
            "subtitle",
            "lead",
            "description",
            "slug",
            Div(
                Div(Submit("save", _("Update email")), css_class="col-sm-10 col-sm-offset-2"),
                css_class="form-group",
            ),
        )
