from django import forms
from django.forms import BaseFormSet
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _

from activities.models import Course
from activities.models import ExtraNeed
from registrations.models import ExtraInfo


class AnswerForm(forms.Form):
    value = forms.CharField(label=_("Answer"), max_length=255)
    price = forms.IntegerField(
        label=_("Price adjustment (CHF)"), required=False, min_value=-2147483648, max_value=2147483647
    )


class AnswerFormSet(BaseFormSet):
    def clean(self):
        if any(self.errors):
            return
        values = [
            form.cleaned_data["value"]
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if len(values) != len(set(values)):
            raise forms.ValidationError(_("Each answer must be unique."))


Answers = formset_factory(AnswerForm, formset=AnswerFormSet, extra=0, can_delete=True, max_num=100, validate_max=True)


class QuestionForm(forms.ModelForm):
    confirm_changes = forms.BooleanField(
        required=False,
        label=_("I confirm these changes despite their impact on existing answers and amounts."),
    )

    no_price = forms.IntegerField(
        label=_("No — price adjustment (CHF)"), required=False, initial=0, min_value=-2147483648, max_value=2147483647
    )
    yes_price = forms.IntegerField(
        label=_("Yes — price adjustment (CHF)"), required=False, initial=0, min_value=-2147483648, max_value=2147483647
    )
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.select_related("activity").order_by("number"),
        required=False,
        label=_("Courses concerned"),
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = ExtraNeed
        fields = ("question_label", "extra_info", "type", "mandatory", "image_label", "default", "courses")
        labels = {"extra_info": _("Help text"), "mandatory": _("Required answer")}
        widgets = {"extra_info": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = (
            ("B", _("Yes / No")),
            ("C", _("Text or list of choices")),
            ("I", _("Number or list of numbers")),
            ("IM", _("Yes / No with an image")),
        )
        self.fields["extra_info"].help_text = _("Additional instructions shown to families.")
        self.fields["default"].help_text = _("Optional. For a yes/no question, use 0 for No or 1 for Yes.")
        self.fields["courses"].help_text = _("These courses will offer this question during registration.")
        self.original_type = self.instance.type
        self.original_choices = list(self.instance.choices or [])
        self.original_prices = list(self.instance.price_modifier or [])
        self.has_answers = bool(self.instance.pk and ExtraInfo.objects.filter(key=self.instance).exists())
        if self.instance.pk and self.instance.type in ("B", "IM"):
            self.initial["no_price"] = self.instance.price_dict.get("0", 0)
            self.initial["yes_price"] = self.instance.price_dict.get("1", 0)
        rows = [
            {"value": value, "price": self.original_prices[i] if i < len(self.original_prices) else 0}
            for i, value in enumerate(self.original_choices)
        ]
        self.answers = Answers(
            self.data if self.is_bound else None, initial=None if self.is_bound else rows, prefix="answers"
        )

    def clean_answers(self, data):
        if data.get("type") in ("B", "IM"):
            choices = self.original_choices if data.get("type") == self.original_type else []
            return choices, [data.get("no_price") or 0, data.get("yes_price") or 0]
        if not self.answers.is_valid():
            raise forms.ValidationError(_("Please correct the answers below."))
        rows = [f.cleaned_data for f in self.answers if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        choices = [row["value"] for row in rows]
        if data.get("type") == "I":
            for value in choices:
                try:
                    int(value)
                except ValueError:
                    raise forms.ValidationError(_("All answers must be whole numbers."))
        return choices, [row.get("price") or 0 for row in rows]

    def clean(self):
        data = super().clean()
        question_type = data.get("type")
        choices, prices = self.clean_answers(data)
        default = data.get("default", "")
        allowed = ["0", "1"] if question_type in ("B", "IM") else choices
        if default and allowed and default not in allowed:
            self.add_error("default", _("The default must be one of the answers."))
        if default and question_type == "I":
            try:
                int(default)
            except ValueError:
                self.add_error("default", _("Enter a whole number."))
        original_prices = self.original_prices or [0] * (
            2 if self.original_type in ("B", "IM") else len(self.original_choices)
        )
        self.requires_confirmation = self.has_answers and (
            question_type != self.original_type or choices != self.original_choices or prices != original_prices
        )
        if self.requires_confirmation and not data.get("confirm_changes"):
            self.add_error("confirm_changes", _("Confirm the impact on existing answers before saving."))
        self.instance.choices = choices
        self.instance.price_modifier = prices
        return data
