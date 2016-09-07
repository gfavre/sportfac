from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from profiles.models import SchoolYear
from .models import Teacher


class TeacherForm(forms.ModelForm):
    
    years = forms.ModelMultipleChoiceField(queryset=SchoolYear.visible_objects.all())
    
    class Meta:
        model = Teacher
        fields = ('first_name', 'last_name', 'email', 'years')


class TeacherImportForm(forms.Form):
    thefile = forms.FileField(label=_("File"), help_text=_("Extraction from LAGAPEO, excel format"))