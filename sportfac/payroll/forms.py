from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, ButtonHolder
import floppyforms.__future__ as forms

from .models import Function, Payroll


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


class PayrollExportForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = ('set_as_exported', 'include_already_exported', 'add_details')

    def __init__(self, *args, **kwargs):
        super(PayrollExportForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.layout = Layout(
            'set_as_exported',
            'include_already_exported',
            'add_details',
            ButtonHolder(Submit('export', _("Export to csv"), css_class='btn-primary'), css_class='col-sm-offset-2'),
        )