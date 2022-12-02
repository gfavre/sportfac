# -*- coding: utf-8 -*-
from __future__ import absolute_import
import datetime

import floppyforms.__future__ as forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db.models import Case, IntegerField, Sum, When
from django.forms import inlineformset_factory
from django.forms.widgets import TextInput
from django.utils.text import mark_safe
from django.utils.translation import ugettext as _

from activities.models import Course, ExtraNeed
from registrations.models import Child, ExtraInfo, Registration
from .models import YearTenant
from six.moves import zip


class ChildImportForm(forms.Form):
    thefile = forms.FileField(label=_("File"), help_text=_("Extraction from LAGAPEO, excel format"))


class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'floppyforms/datetime.html'


class DatePickerInput(forms.DateInput):
    template_name = 'floppyforms/date.html'

    def __init__(self, attrs=None, format=None):
        if not format:
            self.format = '%d.%m.%Y'
        super(DatePickerInput, self).__init__(attrs, format=format)

    def format_value(self, value):
        try:
            return value.strftime('%d.%m.%Y')
        except AttributeError:
            return value


class MultiDateInput(DatePickerInput):
    template_name = 'floppyforms/date-multiple.html'


class TimePickerInput(forms.TimeInput):
    template_name = 'floppyforms/time.html'


class Select2Widget(forms.Select):
    template_name = 'floppyforms/select2.html'


class Select2MultipleWidget(forms.SelectMultiple):
    template_name = 'floppyforms/select2.html'

    def build_attrs(self, extra_attrs=None, **kwargs):
        self.attrs.setdefault('multiple', 'multiple')
        return super(Select2MultipleWidget, self).build_attrs(extra_attrs, **kwargs)


class RegistrationDatesForm(forms.Form):
    opening_date = forms.DateTimeField(label=_("Opening date"), required=True,
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))
    closing_date = forms.DateTimeField(label=_("Closing date"), required=True,
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))

    def clean(self):
        opening_date = self.cleaned_data.get('opening_date')
        closing_date = self.cleaned_data.get('closing_date')
        if opening_date and closing_date and not opening_date < closing_date:
            raise forms.ValidationError(_("Closing date should come after opening date"))
        super(RegistrationDatesForm, self).clean()


class CourseSelectMixin(object):
    course = forms.ModelChoiceField(label=_("Course"),
                                    queryset=Course.objects,
                                    empty_label=None,
                                    widget=Select2Widget())

    def __init__(self, *args, **kwargs):
        super(CourseSelectMixin, self).__init__(*args, **kwargs)
        course_qs = Course.objects.select_related('activity')
        if self.instance.pk:
            # course_qs = course_qs.filter(
            #    Q(pk=self.instance.course.pk) | Q(nb_participants__lt=F('max_participants'))
            # )
            #course_qs = course_qs.filter(pk=self.instance.course.pk)
            course_qs = course_qs.all()
        # else:
        #    course_qs = course_qs.filter(nb_participants__lt=F('max_participants'))
        try:
            if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
                if self.instance.child.school_year:
                    min_year = max_year = self.instance.child.school_year.year
                else:
                    min_year = 99
                    max_year = 0
                course_qs = course_qs.filter(
                    schoolyear_min__lte=min_year,
                    schoolyear_max__gte=max_year,
                )
            else:
                course_qs = course_qs.filter(
                    max_birth_date__lte=self.instance.child.birth_date,
                    min_birth_date__gte=self.instance.child.birth_date,
                )
        except Child.DoesNotExist:
            pass
        self.fields['course'].queryset = course_qs


class RegistrationForm(CourseSelectMixin, forms.ModelForm):
    child = forms.ModelChoiceField(label=_("Child"),
                                   queryset=Child.objects.exclude(family=None),
                                   empty_label=None,
                                   widget=Select2Widget())

    status = forms.ChoiceField(label=_("Status"), choices=Registration.STATUS)

    class Meta:
        model = Registration
        fields = ('child', 'course', 'status', 'transport')
        widgets = {'course': Select2Widget()}

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        if not settings.KEPCHUP_DISPLAY_CAR_NUMBER:
            del self.fields['transport']


class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, datetime.date):
            value = value.strftime('%d-%m-%Y')
        markup = u'<p class="form-control-static">{}</p>'

        return mark_safe(markup.format(value))


class PlainTextExtraNeedWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        extra = ExtraNeed.objects.get(pk=value)
        value = extra.question_label
        markup = u'<p class="form-control-static">{}</p>'
        return mark_safe(markup.format(value))


class ExtraInfoForm(forms.ModelForm):
    key = forms.ModelChoiceField(label=_("Question"),
                                 queryset=ExtraNeed.objects.all(),
                                 empty_label=None,
                                 disabled=True,
                                 widget=PlainTextExtraNeedWidget)
    value = forms.CharField(required=True, label=_("Answer"))

    class Meta:
        model = ExtraInfo
        fields = ('key', 'value')
        read_only = ('key',)

    def __init__(self, *args, **kwargs):
        super(ExtraInfoForm, self).__init__(*args, **kwargs)
        if self.instance:
            if self.instance.key.choices:
                self.fields['value'] = forms.ChoiceField(choices=[('', '----')] + list(zip(self.instance.key.choices,
                                                                                      self.instance.key.choices)),

                                                         label=_("Answer"))
            elif self.instance.type == 'B':
                self.fields['value'] = forms.BooleanField(label=_("Answer"))

            elif self.instance.type == 'I':
                self.fields['value'] = forms.IntegerField(label=_("Answer"))


ExtraInfoFormSet = inlineformset_factory(Registration, ExtraInfo, form=ExtraInfoForm, fields=('key', 'value'),
                                         extra=0, can_delete=False)


class ChildSelectForm(forms.ModelForm):
    """Child selection, with select2 widget.
       Used in registration creation wizard"""
    child = forms.ModelChoiceField(label=_("Child"),
                                   queryset=Child.objects.exclude(family=None),
                                   empty_label=None,
                                   widget=Select2Widget())

    class Meta:
        model = Registration
        fields = ('child',)


class CourseSelectForm(CourseSelectMixin, forms.ModelForm):
    """Course selection, used in registration creation wizard"""

    def __init__(self, *args, **kwargs):
        super(CourseSelectForm, self).__init__(*args, **kwargs)
        course_qs = self.fields['course'].queryset
        # do not offer registrations to already registered courses.
        try:
            if self.instance.child.registrations.count():
                course_qs = course_qs.exclude(pk__in=[registration.course.pk for registration in
                                                      self.instance.child.registrations.all()])
        except Child.DoesNotExist:
            pass
        self.fields['course'].queryset = course_qs

    class Meta:
        model = Registration
        fields = ('course',)
        widgets = {'course': Select2Widget}


class SendConfirmationForm(forms.Form):
    send_confirmation = forms.BooleanField(required=False, label=_("Send confirmation email?"), initial=True)


class BillingForm(forms.ModelForm):
    paid = forms.BooleanField(required=False, label=_("Mark as paid?"),
                              help_text=_("If not checked, a bill will be created"))
    send_confirmation = forms.BooleanField(required=False, initial=True, label=_("Send confirmation email?"))

    class Meta:
        model = Registration
        fields = ('paid', 'send_confirmation')


class SessionForm(forms.Form):
    date = forms.DateField(label=_("Session date"), required=True,
                           help_text=_("Format: DD.MM.YYYY"),
                           widget=DatePickerInput(),
                           initial=datetime.date.today())


class YearSelectForm(forms.Form):
    tenant = forms.ModelChoiceField(label=_("Period"), queryset=YearTenant.objects.all(), required=True)
    next = forms.CharField(max_length=255, required=True)


class YearCreateForm(forms.Form):
    start_date = forms.DateField(label=_("Period start date"), required=True,
                                 help_text=_("Format: DD.MM.YYYY"),
                                 widget=DatePickerInput())
    end_date = forms.DateField(label=_("Period end date"), required=True,
                               help_text=_("Format: DD.MM.YYYY"),
                               widget=DatePickerInput())
    copy_activities = forms.ModelChoiceField(
        label=_("Copy courses"),
        help_text=_("Copy all activities and courses from the selected period"),
        queryset=YearTenant.objects.all(), required=False)
    copy_children = forms.ModelChoiceField(
        label=_("Copy children"),
        help_text=_("Copy all children from the selected period"),
        queryset=YearTenant.objects.all(), required=False)


class YearForm(forms.ModelForm):
    start_date = forms.DateField(label=_("Period start date"), required=True,
                                 help_text=_("Format: DD.MM.YYYY"),
                                 widget=DatePickerInput())
    end_date = forms.DateField(label=_("Period end date"), required=True,
                               help_text=_("Format: DD.MM.YYYY"),
                               widget=DatePickerInput())

    class Meta:
        model = YearTenant
        fields = ('start_date', 'end_date')

    def __init__(self, *args, **kwargs):
        super(YearForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = 'form-horizontal'
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
        #self.helper.form_group_wrapper_class = 'row'
        #self.helper.label_class = 'col-sm-2'
        #self.helper.field_class = 'col-sm-10'


class PayslipMontreuxForm(forms.Form):
    function = forms.CharField(label=_("Function"), required=True)
    rate_mode = forms.ChoiceField(label=_("Rate mode"),
                                  choices=(('day', _("Daily")),
                                           ('hour', _("Hourly"))),
                                  widget=forms.RadioSelect
                                  )
    rate = forms.DecimalField(label=_("Rate"), max_digits=6, decimal_places=2, required=True, widget=TextInput())
    start_date = forms.DateField(label=_("Start date"), required=True,
                                 help_text=_("Format: DD.MM.YYYY"),
                                 widget=DatePickerInput())
    end_date = forms.DateField(label=_("End date"), required=True,
                               help_text=_("Format: DD.MM.YYYY"),
                               widget=DatePickerInput())

    def __init__(self, *args, **kwargs):
        super(PayslipMontreuxForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'


class FlatPageForm(forms.ModelForm):
    content = forms.CharField(
        label=_("Content"),
        widget=CKEditorUploadingWidget(config_name='default', extra_plugins=None, external_plugin_resources=None)
    )

    class Meta:
        model = FlatPage
        fields = ('title', 'content')

    def __init__(self, *args, **kwargs):
        super(FlatPageForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_group_wrapper_class = 'row'
        self.helper.label_class = 'col-sm-2'
        self.helper.field_class = 'col-sm-10'
