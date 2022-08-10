import floppyforms.__future__ as forms

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout

from .models import Function


class FunctionForm(forms.ModelForm):
    class Meta:
        model = Function
        fields = ['code', 'name', 'rate', 'rate_mode']

    def __init__(self, *args, **kwargs):
        super(FunctionForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.layout = Layout(
            'code',
            'name',
            'rate',
            'rate_mode',
        )