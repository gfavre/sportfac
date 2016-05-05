from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from .models import Child
from backend.forms import Select2Widget, DatePickerInput
from schools.models import Teacher


class ChildForm(forms.ModelForm):
    birth_date = forms.DateTimeField(widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("Format: 31.12.2012"))
    sex = forms.ChoiceField(widget=forms.widgets.RadioSelect, choices=Child.SEX)
    teacher = forms.ModelChoiceField(queryset=Teacher.objects.prefetch_related('years'), 
                                     empty_label=None,
                                     widget=Select2Widget()) 
    class Meta:
        model = Child
        fields = ('first_name', 'last_name', 'sex', 'birth_date', 'nationality', 
                  'language', 'school_year', 'teacher')
