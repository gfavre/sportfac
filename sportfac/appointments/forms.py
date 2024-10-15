from django import forms
from django.utils.translation import gettext_lazy as _

from registrations.models import Child


class RentalSelectionForm(forms.Form):
    children = forms.ModelMultipleChoiceField(
        label=_("Rent equipment for these children"),
        queryset=None,  # We'll set this in the view to only show the current user's children
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields["children"].queryset = Child.objects.filter(family=user)
