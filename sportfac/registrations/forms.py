from django.conf import settings
from django.db.models import Count, Case, When, IntegerField
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from .models import Bill, Child, Registration, Transport
from activities.models import Activity, Course
from backend.forms import Select2Widget, DatePickerInput
from profiles.models import FamilyUser, School, SchoolYear
from schools.models import Building, Teacher


class BillForm(forms.ModelForm):
    status = forms.ChoiceField(choices=list(Bill.STATUS)[1:])

    class Meta:
        model = Bill
        fields = ('status',)


class ChildForm(forms.ModelForm):
    birth_date = forms.DateTimeField(label=_("Birth date"),
                                     widget=DatePickerInput(format='%d.%m.%Y'),
                                     help_text=_("Format: 31.12.2012"))
    sex = forms.ChoiceField(label=_("Sex"),widget=forms.widgets.RadioSelect, choices=Child.SEX)
    teacher = forms.ModelChoiceField(label=_("Teacher"),
                                     queryset=Teacher.objects.prefetch_related('years'),
                                     widget=Select2Widget(),
                                     required=False)
    building = forms.ModelChoiceField(label=_("Building"),
                                     queryset=Building.objects.all(),
                                     widget=Select2Widget(),
                                     required=False)
    nationality = forms.ChoiceField(label=_("Nationality"), choices=Child.NATIONALITY)
    language = forms.ChoiceField(label=_("Language"), choices=Child.LANGUAGE)
    school_year = forms.ModelChoiceField(label=_("School year"),
                                         queryset=SchoolYear.visible_objects.all(), required=False)
    family = forms.ModelChoiceField(
        label=_("Parent"), queryset=FamilyUser.active_objects.all(), widget=Select2Widget(), required=False
    )
    id_lagapeo = forms.IntegerField(label=_("SSF number"), required=False)

    school = forms.ModelChoiceField(label=_("School"),
                                    queryset=School.objects.filter(selectable=True),
                                    required=False)
    emergency_number = forms.CharField(label=_("Emergency number"), required=False)
    bib_number = forms.CharField(label=_("Bib number"), required=False)

    class Meta:
        model = Child
        fields = ('id_lagapeo', 'family', 'first_name', 'last_name', 'sex', 'birth_date', 'nationality',
                  'language', 'school', 'other_school', 'school_year', 'teacher', 'building', 'emergency_number',
                  'bib_number', 'is_blacklisted')

    def __init__(self, *args, **kwargs):
        super(ChildForm, self).__init__(*args, **kwargs)
        if not settings.KEPCHUP_USE_BUILDINGS:
            del self.fields['building']

    def clean_id_lagapeo(self):
        id_lagapeo = self.cleaned_data["id_lagapeo"]
        if not id_lagapeo:
            return None
        try:
            child = Child.objects.get(id_lagapeo=id_lagapeo)
            if self.instance and self.instance != child:
                raise forms.ValidationError(mark_safe(
        _("This identifer is already attributed to another child.<br>"
          "Please <a href=\"%s\" target=\"_blank\">review and delete the other child account</a>.") % child.get_backend_detail_url()),
                    code='unique'
                )
        except Child.DoesNotExist:
            return id_lagapeo
        return id_lagapeo


class RegistrationModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.detailed_label()


class MoveRegistrationsForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(queryset=Registration.objects.all(),
                                                   widget=forms.MultipleHiddenInput)
    destination = RegistrationModelChoiceField(
            queryset=Course.objects.select_related('activity')\
                                   .annotate(
                nb_participants=Count(Case(
                    When(participants__status__in=['waiting', 'valid', 'confirmed'], then=1),
                    output_field=IntegerField()
                )),
            ),
            widget=Select2Widget()
    )


class MoveTransportForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(queryset=Registration.objects.all(),
                                                   widget=forms.MultipleHiddenInput)
    destination = forms.ModelChoiceField(
            queryset=Transport.objects.all(),
            widget=Select2Widget())


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ('name',)
