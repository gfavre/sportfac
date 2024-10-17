from django import forms
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper

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
        initial_rentals = kwargs.pop("initial_rentals", [])  # Pre-selected rentals
        disabled = kwargs.pop("disabled", False)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = "rental-form"
        if user:
            self.fields["children"].queryset = Child.objects.filter(family=user)
        if initial_rentals:
            # Pre-select the children who already have a rental
            self.initial["children"] = initial_rentals
        if disabled:
            self.fields["children"].widget.attrs["disabled"] = "disabled"
