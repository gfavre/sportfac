from django.utils.translation import ugettext as _

import floppyforms as forms

from constance.admin import config

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
            
