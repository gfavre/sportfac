# -*- coding: utf-8 -*-
from django.db.models import Case, When, F, IntegerField, Q, Sum
from django.forms import inlineformset_factory
from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms

from activities.models import Course, ExtraNeed
from registrations.models import Child, Registration, ExtraInfo
from .models import YearTenant


class ChildImportForm(forms.Form):
    thefile = forms.FileField(label=_("File"), help_text=_("Extraction from LAGAPEO, excel format"))


class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'floppyforms/datetime.html'


class DatePickerInput(forms.DateInput):
    template_name = 'floppyforms/date.html'

    def __init__(self, attrs=None, format=None):
        super(DatePickerInput, self).__init__(attrs)
        if not format:
            self.format = '%d.%m.%Y'


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
        course_qs = Course.objects.select_related('activity').annotate(
                        nb_participants=Sum(
                            Case(
                                When(participants__status__in=(Registration.STATUS.valid,
                                                               Registration.STATUS.waiting,
                                                               Registration.STATUS.confirmed),
                                     then=1),
                                default=0,
                                output_field=IntegerField()
                            )
                        )
        )
        if self.instance.pk:
            course_qs = course_qs.filter(
                 Q(pk=self.instance.course.pk) | Q(nb_participants__lt=F('max_participants'))
            )
        else:
            course_qs = course_qs.filter(nb_participants__lt=F('max_participants'))
        try:
            if self.instance.child.school_year:
                min_year = max_year = self.instance.child.school_year.year
            else:
                min_year = 99
                max_year = 0
            course_qs = course_qs.filter(
                schoolyear_min__lte=min_year,
                schoolyear_max__gte=max_year,
            )
        except Child.DoesNotExist:
            pass
        self.fields['course'].queryset = course_qs.prefetch_related('participants')


class RegistrationForm(CourseSelectMixin, forms.ModelForm):
    child = forms.ModelChoiceField(label=_("Child"),
                                   queryset=Child.objects.exclude(family=None),
                                   empty_label=None,
                                   widget=Select2Widget())

    status = forms.ChoiceField(label=_("Status"), choices=Registration.STATUS)

    class Meta:
        model = Registration
        fields = ('child', 'course', 'status')


class ExtraInfoForm(forms.ModelForm):
    key = forms.ModelChoiceField(label=_("Question"),
                                 queryset=ExtraNeed.objects,
                                 empty_label=None,
                                 disabled=True)
    value = forms.CharField(required=True, label=_("Value"))

    class Meta:
        model = ExtraInfo
        fields = ('key', 'value')

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


class BillingForm(forms.ModelForm):
    paid = forms.BooleanField(required=False, label=_("Mark as paid?"),
                              help_text=_("If not checked, a bill will be created"))

    class Meta:
        model = Registration
        fields = ('paid',)


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


class PayslipMontreuxForm(forms.Form):
    function = forms.CharField(label=_("Function"), required=True)
    rate_mode = forms.ChoiceField(label=_("Rate mode"),
                                  choices=(('day', _("Daily")),
                                           ('hour', _("Hourly"))),
                                  widget=forms.RadioSelect
                                  )
    rate = forms.DecimalField(label=_("Rate"), max_digits=6, decimal_places=2, required=True)
