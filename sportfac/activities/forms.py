import floppyforms.__future__ as forms

from .models import Activity, Course


class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'floppyforms/datetime.html'

class Select2Widget(forms.Select):
    template_name = 'floppyforms/select2.html'

            

class CourseForm(forms.ModelForm):
    #activity = forms.ModelChoiceField(queryset=Activity.objects, 
    #                                  empty_label=None,
    #                                  widget=Select2Widget())    

    
    class Meta:
        model = Course
        fields = ('activity', 'number', 'responsible', 'price', 
                  'number_of_sessions', 'day', 'start_date', 'end_date',
                  'start_time', 'end_time', 'place', 'min_participants',
                  'max_participants', 'schoolyear_min', 'schoolyear_max')
        