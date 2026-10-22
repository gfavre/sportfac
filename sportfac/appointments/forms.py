from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Layout
from django import forms
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from registrations.models import Child

from .models import Appointment
from .models import AppointmentSlot


class RentalSelectionForm(forms.Form):
    disabled_children = forms.ModelMultipleChoiceField(
        label=_("Children who already have a rental"),
        queryset=Child.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    children = forms.ModelMultipleChoiceField(
        label=_("Rent equipment for these children"),
        queryset=Child.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        initial_rentals = kwargs.pop("initial_children", [])  # Pre-selected rentals
        disabled_children_initial = kwargs.pop("disabled_children_initial", [])  # Pre-selected rentals

        # if not disabled_children_initial:
        #    self.fields.pop
        disabled = kwargs.pop("disabled", False)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_id = "rental-form"
        self.helper.form_class = "equipment-card equipment-children-card"
        self.helper.layout = Layout(
            HTML('{% load i18n %}<h2 class="equipment-section-title">{% translate "Enfants concernés" %}</h2>'),
            "disabled_children",
            "children",
        )
        if disabled_children_initial:
            self.fields["children"].queryset = (
                Child.objects.filter(family=user, registrations__isnull=False)
                .distinct()
                .exclude(id__in=disabled_children_initial)
            )
            self.fields["disabled_children"].queryset = disabled_children_initial
            self.initial["disabled_children"] = disabled_children_initial  # all are checked
            self.fields["disabled_children"].widget.attrs["disabled"] = "disabled"
        else:
            self.fields["children"].queryset = Child.objects.filter(
                family=user, registrations__isnull=False
            ).distinct()
            self.fields["disabled_children"].widget = forms.HiddenInput()

        if initial_rentals:
            # Pre-select the children who already have a rental
            self.initial["children"] = initial_rentals
        if disabled:
            self.fields["children"].widget.attrs["disabled"] = "disabled"
            self.fields["children"].label = ""
            self.fields["disabled_children"].label = ""
            self.helper.layout.insert(
                1,
                HTML(
                    '{% load i18n %}<p class="equipment-help">'
                    '{% translate "Le rendez-vous de retour concerne le matériel loué pour ces enfants." %}</p>'
                ),
            )


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["child", "slot"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["child"].disabled = True
        self.fields["slot"].queryset = (
            AppointmentSlot.objects.with_available_places()
            .filter(start__gte=now())
            .filter(Q(count_available_places__gt=0) | Q(pk=self.instance.slot_id))
            .order_by("start", "end")
        )
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.form_group_wrapper_class = "row"
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
