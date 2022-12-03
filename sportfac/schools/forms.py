from __future__ import absolute_import

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms
from profiles.models import SchoolYear

from .models import Building, Teacher


class TeacherForm(forms.ModelForm):
    years = forms.ModelMultipleChoiceField(
        label=_("Years"), queryset=SchoolYear.visible_objects.all()
    )

    class Meta:
        model = Teacher
        fields = ("first_name", "last_name", "email", "years", "buildings")


class TeacherImportForm(forms.Form):
    building = forms.ModelChoiceField(
        queryset=Building.objects.all(), required=False, empty_label=_("No building information")
    )
    thefile = forms.FileField(
        label=_("File"), help_text=_("Extraction from LAGAPEO, excel format")
    )

    def __init__(self, *args, **kwargs):
        super(TeacherImportForm, self).__init__(*args, **kwargs)
        if not settings.KEPCHUP_USE_BUILDINGS:
            del self.fields["building"]


class BuildingForm(forms.ModelForm):
    class Meta:
        model = Building
        fields = ("name", "address", "zipcode", "city", "country")
