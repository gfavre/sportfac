from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms

from backend.forms import Select2Widget, Select2MultipleWidget, DatePickerInput, TimePickerInput
from .models import Activity, Course

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
    number = forms.CharField(label=_("Identifier"), required=True)
    price = forms.DecimalField(label=_("Price"), required=True)

    start_date = forms.DateTimeField(label=_("Start date"), required=True, 
                                     widget=DatePickerInput(format='%d.%m.%Y'))
    end_date = forms.DateTimeField(label=_("End date"), required=True, 
                                   widget=DatePickerInput(format='%d.%m.%Y'))
    start_time = forms.TimeField(label=_("Start time"), required=True, 
                                 widget=TimePickerInput(format='%H:%M'))
    end_time = forms.TimeField(label=_("End time"), required=True, 
                               widget=TimePickerInput(format='%H:%M'))
    
    class Meta:
        model = Course
        fields = ('activity', 'number', 'instructors', 'price', 
                  'number_of_sessions', 'day', 'start_date', 'end_date',
                  'start_time', 'end_time', 'place', 'min_participants',
                  'max_participants', 'schoolyear_min', 'schoolyear_max', 
                  'uptodate', 'visible')


class ActivityForm(forms.ModelForm):
    number = forms.CharField(label=_("Identifier"), required=True)
    
    class Meta:
        model = Activity
        fields = ('name', 'number', 'description', 'informations')
