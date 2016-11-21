from django.conf import settings
from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms

from backend.forms import Select2Widget, Select2MultipleWidget, DatePickerInput, TimePickerInput
from .models import Activity, Course, ExtraNeed
from profiles.models import FamilyUser


            

class CourseForm(forms.ModelForm):
    activity = forms.ModelChoiceField(label=_("Activity"),
                                      queryset=Activity.objects, 
                                      empty_label=None,
                                      widget=Select2Widget())    
    instructors = forms.ModelMultipleChoiceField(
        label=_("Instructors"),
        queryset=FamilyUser.objects, 
        widget=Select2MultipleWidget()
    )
    name = forms.CharField(label=_("Displayed name (optional)"), required=False, help_text=_("Displayed on calendar under activity name"))
    number = forms.CharField(label=_("Identifier"), required=True)
    price = forms.DecimalField(label=_("Price"), initial=0, required=True, 
                               widget=settings.KEPCHUP_NO_PAYMENT and forms.HiddenInput or forms.NumberInput)

    start_date = forms.DateTimeField(label=_("Start date"), required=True, 
                                     widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("format: dd.mm.yyyy, e.g. 31.07.2016"))
    end_date = forms.DateTimeField(label=_("End date"), required=True, 
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
        fields = ('activity', 'name', 'number', 'instructors', 'price',
                  'number_of_sessions', 'day', 'start_date', 'end_date',
                  'start_time', 'end_time', 'place', 'min_participants',
                  'max_participants', 'schoolyear_min', 'schoolyear_max', 
                  'uptodate', 'visible', 'extra')


class ActivityForm(forms.ModelForm):
    number = forms.CharField(label=_("Identifier"), required=True)
    
    class Meta:
        model = Activity
        fields = ('name', 'number', 'description', 'informations')
