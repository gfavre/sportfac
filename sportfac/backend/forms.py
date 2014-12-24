from django.utils.translation import ugettext as _
from django.db.models import Count, F, Q

import floppyforms.__future__ as forms
from constance.admin import config

from activities.models import Course
from profiles.models import Registration

class DateTimePickerInput(forms.DateTimeInput):
    template_name = 'floppyforms/datetime.html'


class RegistrationDatesForm(forms.Form):
    opening_date = forms.DateTimeField(label=_("Opening date"), required=True, 
                                       initial=config.START_REGISTRATION,
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))
    closing_date = forms.DateTimeField(label=_("Closing date"), required=True,
                                       initial=config.END_REGISTRATION, 
                                       widget=DateTimePickerInput(format='%d.%m.%Y %H:%M'))
    
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
                 Q(pk=self.instance.course.pk) | Q(nb_participants__lt=F('max_participants')),
                 schoolyear_min__lte=self.instance.child.school_year.year,
                 schoolyear_max__gte=self.instance.child.school_year.year)
                 
        else:
            course_qs = course_qs.filter(nb_participants__lt=F('max_participants')) 
            
        self.fields['course'].queryset = course_qs


class RegistrationUpdateForm(RegistrationForm):
    class Meta:
        model = Registration
        fields = ( 'course',)
        widgets = {
            'status': forms.RadioSelect,
        }
