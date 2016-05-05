from django.utils.translation import ugettext_lazy as _

import floppyforms.__future__ as forms

from .models import Teacher


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ('first_name', 'last_name', 'email', 'years')


class TeacherImportForm(forms.Form):
    thefile = forms.FileField(label=_("File"), help_text=_("Extraction from LAGAPEO, excel format"))