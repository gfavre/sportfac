from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from .models import Bill, Child
from backend.forms import Select2Widget, DatePickerInput
from profiles.models import FamilyUser, SchoolYear
from schools.models import Teacher


class ChildForm(forms.ModelForm):
    birth_date = forms.DateTimeField(label=_("Birth date"),
                                     widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("Format: 31.12.2012"))
    sex = forms.ChoiceField(label=_("Sex"),widget=forms.widgets.RadioSelect, choices=Child.SEX)
    teacher = forms.ModelChoiceField(label=_("Teacher"),
                                     queryset=Teacher.objects.prefetch_related('years'), 
                                     widget=Select2Widget(),
                                     required=False)
    nationality = forms.ChoiceField(label=_("Nationality"), choices=Child.NATIONALITY)
    language = forms.ChoiceField(label=_("Language"), choices=Child.LANGUAGE)
    school_year = forms.ModelChoiceField(label=_("School year"), 
                                         queryset=SchoolYear.objects.all(), required=False)
    family = forms.ModelChoiceField(label=_("Parent"),
                                     queryset=FamilyUser.objects.all(), 
                                     widget=Select2Widget(),
                                     required=False)
    id_lagapeo = forms.IntegerField(label=_("Identifier"), required=False)
    
    class Meta:
        model = Child
        fields = ('id_lagapeo', 'family', 'first_name', 'last_name', 'sex', 'birth_date', 'nationality', 
                  'language', 'school_year', 'teacher')


class BillForm(forms.ModelForm):
    class Meta:
        model = Bill
        fields = ('status',)
