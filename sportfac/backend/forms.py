from django.db.models import Count, F, Q
from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms
from constance.admin import config

from activities.models import Course
from profiles.models import Child
from registrations.models import Registration
from .models import YearTenant

class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'floppyforms/datetime.html'


class DatePickerInput(forms.DateInput):
    template_name = 'floppyforms/date.html'
    
    def __init__(self, attrs=None, format=None):
        super(DatePickerInput, self).__init__(attrs)
        self.format = '%d.%m.%Y'


class TimePickerInput(forms.TimeInput):
    template_name = 'floppyforms/time.html'


class Select2Widget(forms.Select):
    template_name = 'floppyforms/select2.html'


class RegistrationDatesForm(forms.Form):
    opening_date = forms.DateTimeField(label=_("Opening date"), required=True, 
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))
    closing_date = forms.DateTimeField(label=_("Closing date"), required=True,
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))
    
    def __init__(self, *args, **kwargs):
        super(RegistrationDatesForm, self).__init__(*args, **kwargs)
        self.initial.setdefault('opening_date', config.START_REGISTRATION)
        self.initial.setdefault('closing_date', config.END_REGISTRATION)        
    
    def clean(self):
        opening_date = self.cleaned_data.get('opening_date')
        closing_date = self.cleaned_data.get('closing_date')
        if opening_date and closing_date and not opening_date < closing_date:
            raise forms.ValidationError(_("Closing date should come after opening date"))
        super(RegistrationDatesForm, self).clean()
    
    def save_to_constance(self):
        if self.is_valid():
            config.START_REGISTRATION = self.cleaned_data['opening_date']
            config.END_REGISTRATION = self.cleaned_data['closing_date']


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Registration
        fields = ('child', 'course', 'status')
    
    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        course_qs = Course.objects.select_related('activity').annotate(
                        nb_participants=Count('participants'))
        if self.instance.pk:
            course_qs = course_qs.filter(
                 Q(pk=self.instance.course.pk) | Q(nb_participants__lt=F('max_participants'))
            )
        else:
            course_qs = course_qs.filter(nb_participants__lt=F('max_participants')) 
        try:
            course_qs = course_qs.filter(
                schoolyear_min__lte=self.instance.child.school_year.year,
                schoolyear_max__gte=self.instance.child.school_year.year,
            )
        except Child.DoesNotExist:
            pass
        self.fields['course'].queryset = course_qs.prefetch_related('participants')
        


class ChildSelectForm(forms.ModelForm):
    """Child selection, with select2 widget.
       Used in registration creation wizard"""
    child = forms.ModelChoiceField(queryset=Child.objects, 
                                   empty_label=None,
                                   widget=Select2Widget())    
    class Meta:
        model = Registration
        fields = ('child',)


class CourseSelectForm(RegistrationForm):
    "Course selection, used in registration creation wizard"
    course = forms.ModelChoiceField(queryset=Course.objects, #overriden in __init__!
                                    empty_label=None,
                                    widget=Select2Widget())    
    
    class Meta:
        model = Registration
        fields = ('course',)

class YearSelectForm(forms.Form):
    tenant = forms.ModelChoiceField(queryset=YearTenant.objects.all(), required=True)
    next = forms.CharField(max_length=255, required=True)


class YearCreateForm(forms.Form):
    start_date = forms.DateField(label=_("Period start date"), required=True, 
                                 help_text =_("Format: DD.MM.YYYY"),
                                 widget=DatePickerInput())
    end_date = forms.DateField(label=_("Period end date"), required=True,
                               help_text =_("Format: DD.MM.YYYY"),
                               widget=DatePickerInput())
    copy_activities = forms.ModelChoiceField(
        label=_("Copy courses"), 
        help_text=_("Copy all activities and courses from the selected period"),
        queryset=YearTenant.objects.all(), required=False)


class YearForm(forms.ModelForm):
    start_date = forms.DateField(label=_("Period start date"), required=True, 
                                 help_text =_("Format: DD.MM.YYYY"),
                                 widget=DatePickerInput())
    end_date = forms.DateField(label=_("Period end date"), required=True,
                               help_text =_("Format: DD.MM.YYYY"),
                               widget=DatePickerInput())

    class Meta:
        model = YearTenant
        fields = ('start_date', 'end_date')