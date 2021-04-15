# -*- coding: utf-8 -*-
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.widgets import TextInput
from django.utils.translation import ugettext as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit
import floppyforms.__future__ as forms

from backend.forms import Select2Widget, Select2MultipleWidget, DatePickerInput, TimePickerInput, MultiDateInput
from profiles.models import FamilyUser
from .models import Activity, AllocationAccount, Course, ExtraNeed, PaySlip


class CourseForm(forms.ModelForm):
    activity = forms.ModelChoiceField(label=_("Activity"),
                                      queryset=Activity.objects,
                                      empty_label=None,
                                      widget=Select2Widget())
    instructors = forms.ModelMultipleChoiceField(
        label=_("Instructors"),
        queryset=FamilyUser.active_objects,
        widget=Select2MultipleWidget()
    )
    name = forms.CharField(label=_("Displayed name (optional)"), required=False,
                           help_text=_("Displayed on calendar under activity name"))
    number = forms.CharField(label=_("Identifier"), required=True)
    price = forms.DecimalField(label=_("Price"), initial=0, required=True,
                               widget=settings.KEPCHUP_NO_PAYMENT and forms.HiddenInput or forms.NumberInput)
    price_description = forms.CharField(label=_("Informations about pricing"),
                                        widget=forms.Textarea(attrs={'rows': 3}),
                                        required=False)
    start_date = forms.DateTimeField(label=_("Start date"), required=True,
                                     input_formats=['%d.%m.%Y', '%Y-%m-%d'],
                                     widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("format: dd.mm.yyyy, e.g. 31.07.2016"))
    end_date = forms.DateTimeField(label=_("End date"), required=True,
                                   input_formats=['%d.%m.%Y', '%Y-%m-%d'],
                                   widget=DatePickerInput(format='%d.%m.%Y'),
                                   help_text=_("format: dd.mm.yyyy, e.g. 31.07.2016"))
    start_time = forms.TimeField(label=_("Start time"), required=True,
                                 widget=TimePickerInput(format='%H:%M'),
                                 help_text=_("format: hh:mm, e.g. 17:45"))
    end_time = forms.TimeField(label=_("End time"), required=True,
                               widget=TimePickerInput(format='%H:%M'),
                               help_text=_("format: hh:mm, e.g. 17:45"))

    extra = forms.ModelMultipleChoiceField(queryset=ExtraNeed.objects.all(),
                                           label=_("Extra questions"),
                                           required=False,
                                           widget=Select2MultipleWidget())

    class Meta:
        model = Course
        fields = ('activity', 'name', 'number', 'instructors', 'price', 'price_description',
                  'number_of_sessions', 'day', 'start_date', 'end_date',
                  'start_time', 'end_time', 'place', 'min_participants',
                  'max_participants', 'schoolyear_min', 'schoolyear_max',
                  'comments',
                  'uptodate', 'announced_js', 'visible', 'extra',)


class MultipleDatesField(forms.CharField):
    date_format = '%d.%m.%Y'
    separator = ','
    widget = MultiDateInput()

    def widget_attrs(self, widget):
        attrs = super(MultipleDatesField, self).widget_attrs(widget)
        attrs.update({'format': self.date_format})
        return attrs

    def to_python(self, value):
        try:
            output = [datetime.datetime.strptime(val, self.date_format).date() for val in value.split(self.separator)]
        except (ValueError, TypeError):
            raise ValidationError(_("One of the dates is invalid"), code='invalid')
        return output


class ExplicitDatesCourseForm(CourseForm):
    session_dates = MultipleDatesField(
        label=_("Session dates"),
        help_text=_("Separated by commas, e.g. 31.07.2019,22.08.2019"),
    )

    class Meta:
        model = Course
        fields = ('activity', 'name', 'number', 'instructors', 'price', 'price_description',
                  'start_time', 'end_time', 'place', 'comments', 'min_participants',
                  'max_participants', 'schoolyear_min', 'schoolyear_max',
                  'uptodate', 'announced_js', 'visible', 'extra',)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance']:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            kwargs['initial']['session_dates'] = ','.join(
                [session.date.strftime('%d.%m.%Y') for session in kwargs['instance'].get_sessions()]
            )
        super(ExplicitDatesCourseForm, self).__init__(*args, **kwargs)
        self.fields.pop('start_date')
        self.fields.pop('end_date')

    def save(self, commit=True):
        instance = super(ExplicitDatesCourseForm, self).save(commit=commit)
        dates = self.cleaned_data['session_dates']
        for session in instance.get_sessions():
            if session.date not in dates:
                session.delete()
        for date in dates:
            instance.add_session(date=date)
        return instance


class ActivityForm(forms.ModelForm):
    number = forms.CharField(label=_("Identifier"), required=True)

    class Meta:
        model = Activity
        fields = ('name', 'number', 'description', 'informations', 'allocation_account')

    def __init__(self, *args, **kwargs):
        super(ActivityForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'name',
            'number',
            settings.KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS and 'allocation_account' or '',
            'description',
            'informations',
        )


class AllocationAccountForm(forms.ModelForm):

    class Meta:
        model = AllocationAccount
        fields = ('account', 'name')

    def __init__(self, *args, **kwargs):
        super(AllocationAccountForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'account',
            'name',
        )


class PaySlipForm(forms.ModelForm):

    class Meta:
        model = PaySlip
        fields = ('function', 'rate_mode', 'rate',  'start_date', 'end_date')
        widgets = {'rate': TextInput}

    def __init__(self, *args, **kwargs):
        super(PaySlipForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
