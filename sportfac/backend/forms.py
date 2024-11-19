import datetime
from zipfile import BadZipfile

from django import forms
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet
from django.forms.widgets import TextInput
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

from bootstrap_datepicker_plus.widgets import DateTimePickerInput
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Fieldset, Layout, Submit
from django_select2 import forms as s2forms

from activities.models import Course, ExtraNeed
from registrations.models import Child, ExtraInfo, Registration
from registrations.utils import check_children_load_format
from .models import YearTenant


class ChildImportForm(forms.Form):
    thefile = forms.FileField(label=_("File"), help_text=_("Extraction from LAGAPEO, excel format"))

    def clean(self):
        """
        Custom clean method to validate the uploaded file.
        Returns:
            Dict[str, Any]: Cleaned data of the form fields.
        Raises:
            ValueError: If the file format is unreadable or missing mandatory fields.
        """
        cleaned_data = super().clean()
        filelike = cleaned_data.get("thefile")

        if filelike:
            try:
                check_children_load_format(filelike)
            except BadZipfile as exc:
                raise forms.ValidationError(
                    _("File format is unreadable, Lagapeo export should be a .xlsx file")
                ) from exc
            except (ValueError, KeyError) as exc:
                raise forms.ValidationError(str(exc)) from exc

        return cleaned_data

    def __init__(self, *args, **kwargs):
        """
        Initialize the form with Crispy Form settings.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-3"
        self.helper.layout = Layout(
            "thefile",
        )


class DatePickerInput(forms.widgets.DateInput):
    def __init__(self, attrs=None, format=None):
        if not format:
            self.format = "%d.%m.%Y"
        super().__init__(attrs, format=format)

    def format_value(self, value):
        try:
            return value.strftime("%d.%m.%Y")
        except AttributeError:
            return value


class MultiDateInput(DatePickerInput):
    template_name = "backend/widgets/multidatepicker.html"

    class Media:
        js = [
            "js/vendor/bootstrap-datepicker.js",
            "https://cdnjs.cloudflare.com/ajax/libs/bootstrap-datepicker/1.9.0/locales/bootstrap-datepicker.fr.min.js",
            "js/backend/multidatepicker.js",
        ]


class TimePickerInput(forms.TimeInput):
    template_name = "floppyforms/time.html"

    def render(self, name, value, attrs=None, renderer=None):
        attrs["class"] = "form-control timepicker"
        return super().render(name, value, attrs=attrs, renderer=renderer)


class ActivityWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
        "number__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {"data-minimum-input-length": 0}
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)


class ActivityMultipleWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
        "number__icontains",
    ]


class ChildWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "first_name__icontains",
        "last_name__icontains",
    ]


class CourseWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "activity__name__icontains",
        "name__icontains",
        "number__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {"data-minimum-input-length": 0}
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)


class CityMultipleWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
        "zipcode__icontains",
    ]


class ExtraNeedMultipleWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "question_label__icontains",
    ]


class FamilyUserWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "first_name__icontains",
        "last_name__icontains",
        "email__icontains",
    ]


class FamilyUserMultipleWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "first_name__icontains",
        "last_name__icontains",
        "email__icontains",
    ]


class BuildingWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
        "address__icontains",
        "zip_code__icontains",
        "city__icontains",
    ]


class RegistrationWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "child__first_name__icontains",
        "child__last_name__icontains",
        "course__activity__name__icontains",
        "course__name__icontains",
        "course__number__icontains",
    ]


class TeacherWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "first_name__icontains",
        "last_name__icontains",
        "email__icontains",
    ]


class TransportWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "name__icontains",
    ]

    def build_attrs(self, base_attrs, extra_attrs=None):
        default_attrs = {"data-minimum-input-length": 0}
        default_attrs.update(base_attrs)
        return super().build_attrs(default_attrs, extra_attrs=extra_attrs)


class RegistrationDatesForm(forms.Form):
    opening_date = forms.DateTimeField(
        label=_("Opening date"), required=True, widget=DateTimePickerInput(format="%d.%m.%Y %H:%M")
    )
    closing_date = forms.DateTimeField(
        label=_("Closing date"), required=True, widget=DateTimePickerInput(format="%d.%m.%Y %H:%M")
    )

    def clean(self):
        opening_date = self.cleaned_data.get("opening_date")
        closing_date = self.cleaned_data.get("closing_date")
        if opening_date and closing_date and not opening_date < closing_date:
            raise forms.ValidationError(_("Closing date should come after opening date"))
        super().clean()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-3"
        self.helper.include_media = False
        self.helper.layout = Layout(
            "opening_date",
            "closing_date",
        )


class CourseSelectMixin:
    course = forms.ModelChoiceField(
        label=_("Course"), queryset=Course.objects.all(), empty_label=None, widget=CourseWidget()
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        course_qs = Course.objects.select_related("activity")
        if user and user.is_restricted_manager:
            course_qs = course_qs.filter(activity__in=user.managed_activities.all())
        try:
            if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
                if self.instance.child.school_year:
                    min_year = max_year = self.instance.child.school_year.year
                else:
                    min_year = 99
                    max_year = 0
                course_qs = course_qs.filter(
                    schoolyear_min__lte=min_year,
                    schoolyear_max__gte=max_year,
                )
            else:
                course_qs = course_qs.filter(
                    max_birth_date__lte=self.instance.child.birth_date,
                    min_birth_date__gte=self.instance.child.birth_date,
                )
        except Child.DoesNotExist:
            pass
        self.fields["course"].queryset = course_qs


class RegistrationForm(CourseSelectMixin, forms.ModelForm):
    child = forms.ModelChoiceField(
        label=_("Child"),
        queryset=Child.objects.exclude(family=None),
        empty_label=None,
        widget=ChildWidget(),
    )

    status = forms.ChoiceField(label=_("Status"), choices=Registration.STATUS)

    class Meta:
        model = Registration
        fields = ("child", "course", "status", "transport", "price", "paid")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.include_media = False
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        if not settings.KEPCHUP_DISPLAY_CAR_NUMBER:
            del self.fields["transport"]
        if settings.KEPCHUP_NO_PAYMENT:
            del self.fields["paid"]
            del self.fields["price"]
        self.helper.layout = Layout(
            "child",
            "course",
            "status",
            settings.KEPCHUP_DISPLAY_CAR_NUMBER and "transport" or "",
            not settings.KEPCHUP_NO_PAYMENT
            and Fieldset(
                _("Payment"),
                "price",
                "paid",
            )
            or "",
        )


class PlainTextWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        if hasattr(self, "form_field") and getattr(self.form_field, "queryset", None):
            try:
                value = self.form_field.queryset.get(pk=value)
            except self.form_field.queryset.model.DoesNotExist:
                pass
        if isinstance(value, datetime.date):
            value = value.strftime("%d-%m-%Y")

        markup = '<p class="form-control-static">{}</p>'

        return mark_safe(markup.format(value))


class PlainTextExtraNeedWidget(forms.Widget):
    def render(self, name, value, attrs=None, renderer=None):
        extra = ExtraNeed.objects.get(pk=value)
        value = extra.question_label
        markup = '<p class="form-control-static">{}</p>'
        return mark_safe(markup.format(value))


class ExtraInfoForm(forms.ModelForm):
    key = forms.ModelChoiceField(
        label=_("Question"),
        queryset=ExtraNeed.objects.all(),
        empty_label=None,
        disabled=True,
        widget=PlainTextExtraNeedWidget,
    )
    value = forms.CharField(required=True, label=_("Answer"))

    class Meta:
        model = ExtraInfo
        fields = ("key", "value")
        read_only = ("key",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        if self.instance:
            if self.instance.key.choices:
                self.fields["value"] = forms.ChoiceField(
                    choices=[("", "----")] + list(zip(self.instance.key.choices, self.instance.key.choices)),
                    label=_("Answer"),
                )
            elif self.instance.key.type == "B":
                self.fields["value"] = forms.BooleanField(label=_("Answer"))

            elif self.instance.key.type == "I":
                self.fields["value"] = forms.IntegerField(label=_("Answer"))
        self.helper.layout = Layout("key", "value", HTML("<hr>"))


class HorizontalInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


ExtraInfoFormSet = inlineformset_factory(
    Registration,
    ExtraInfo,
    form=ExtraInfoForm,
    fields=("key", "value"),
    extra=0,
    can_delete=False,
    formset=HorizontalInlineFormSet,
)


class ChildSelectForm(forms.ModelForm):
    """Child selection, with select2 widget.
    Used in registration creation wizard"""

    child = forms.ModelChoiceField(
        label=_("Child"),
        queryset=Child.objects.exclude(family=None),
        empty_label=None,
        widget=ChildWidget(),
    )

    class Meta:
        model = Registration
        fields = ("child",)


class CourseSelectForm(CourseSelectMixin, forms.ModelForm):
    """Course selection, used in registration creation wizard"""

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        course_qs = self.fields["course"].queryset
        if user and user.is_restricted_manager:
            course_qs = course_qs.filter(activity__in=user.managed_activities.all())
        # do not offer registrations to already registered courses.
        try:
            if self.instance.child.registrations.count():
                course_qs = course_qs.exclude(
                    pk__in=[registration.course.pk for registration in self.instance.child.registrations.all()]
                )
        except Child.DoesNotExist:
            pass

        self.fields["course"].queryset = course_qs

    class Meta:
        model = Registration
        fields = ("course",)
        # widgets = {"course": CourseWidget}


class SendConfirmationForm(forms.Form):
    send_confirmation = forms.BooleanField(required=False, label=_("Send confirmation email?"), initial=True)


class BillingForm(forms.ModelForm):
    paid = forms.BooleanField(
        required=False,
        label=_("Mark as paid?"),
        help_text=_("If not checked, a bill will be created"),
    )
    send_confirmation = forms.BooleanField(required=False, initial=True, label=_("Send confirmation email?"))

    class Meta:
        model = Registration
        fields = ("paid", "send_confirmation")


class SessionForm(forms.Form):
    date = forms.DateField(
        label=_("Session date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
        initial=datetime.date.today(),
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize the form with Crispy Form settings.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "form-inline"
        self.helper.field_template = "bootstrap3/layout/inline_field.html"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-3"
        self.helper.layout = Layout(
            "date", Submit(value=_("New session"), name="submit", css_class="btn btn-secondary")
        )


class YearSelectForm(forms.Form):
    tenant = forms.ModelChoiceField(label=_("Period"), queryset=YearTenant.objects.all(), required=True)
    next = forms.CharField(max_length=255, required=True)


class YearCreateForm(forms.Form):
    start_date = forms.DateField(
        label=_("Period start date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )
    end_date = forms.DateField(
        label=_("Period end date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )
    copy_activities = forms.ModelChoiceField(
        label=_("Copy courses"),
        help_text=_("Copy all activities and courses from the selected period"),
        queryset=YearTenant.objects.all(),
        required=False,
    )
    copy_children = forms.ModelChoiceField(
        label=_("Copy children"),
        help_text=_("Copy all children from the selected period"),
        queryset=YearTenant.objects.all(),
        required=False,
    )


class YearForm(forms.ModelForm):
    start_date = forms.DateField(
        label=_("Period start date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )
    end_date = forms.DateField(
        label=_("Period end date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )

    class Meta:
        model = YearTenant
        fields = ("start_date", "end_date")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        # self.helper.form_group_wrapper_class = 'row'
        # self.helper.label_class = 'col-sm-2'
        # self.helper.field_class = 'col-sm-10'


class PayslipMontreuxForm(forms.Form):
    function = forms.CharField(label=_("Function"), required=True)
    rate_mode = forms.ChoiceField(
        label=_("Rate mode"),
        choices=(("day", _("Daily")), ("hour", _("Hourly"))),
        widget=forms.RadioSelect,
    )
    rate = forms.DecimalField(label=_("Rate"), max_digits=6, decimal_places=2, required=True, widget=TextInput())
    start_date = forms.DateField(
        label=_("Start date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )
    end_date = forms.DateField(
        label=_("End date"),
        required=True,
        help_text=_("Format: DD.MM.YYYY"),
        widget=DatePickerInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class FlatPageForm(forms.ModelForm):
    content = forms.CharField(
        label=_("Content"),
        widget=CKEditorUploadingWidget(config_name="default", extra_plugins=None, external_plugin_resources=None),
    )

    class Meta:
        model = FlatPage
        fields = ("title", "content")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
