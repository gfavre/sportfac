from django.conf import settings
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from .models import Bill, Child, Registration, Transport
from activities.models import Course
from backend.forms import Select2Widget, DatePickerInput
from profiles.models import FamilyUser, School, SchoolYear
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
                                         queryset=SchoolYear.visible_objects.all(), required=False)
    family = forms.ModelChoiceField(label=_("Parent"),
                                     queryset=FamilyUser.objects.all(), 
                                     widget=Select2Widget(),
                                     required=False)
    id_lagapeo = forms.IntegerField(label=_("SSF number"), required=False)
    
    school = forms.ModelChoiceField(label=_("School"), queryset=School.objects.all(), required=False)
    emergency_number = forms.CharField(label=_("Emergency number"), required=settings.KEPCHUP_EMERGENCY_NUMBER_MANDATORY)
    bib_number = forms.CharField(label=_("Bib number"), required=False)
    
    class Meta:
        model = Child
        fields = ('id_lagapeo', 'family', 'first_name', 'last_name', 'sex', 'birth_date', 'nationality', 
                  'language', 'school', 'other_school', 'school_year', 'teacher', 'emergency_number',
                  'bib_number')


class BillForm(forms.ModelForm):
    status = forms.ChoiceField(choices=list(Bill.STATUS)[1:])
    
    class Meta:
        model = Bill
        fields = ('status',)


class RegistrationModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.detailed_label()


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ('name',)

class MoveRegistrationsForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(queryset=Registration.objects.all(),
                                                   widget=forms.MultipleHiddenInput)
    destination = RegistrationModelChoiceField(
            queryset=Course.objects.select_related('activity')\
                                   .annotate(nb_participants=Count('participants')),
            widget=Select2Widget())


class MoveTransportForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(queryset=Registration.objects.all(),
                                                   widget=forms.MultipleHiddenInput)
    destination = forms.ModelChoiceField(
            queryset=Transport.objects.all(),
            widget=Select2Widget())