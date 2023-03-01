import datetime

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.widgets import TextInput
from django.utils.translation import gettext as _

from backend.forms import (
    ActivityWidget,
    CityMultipleWidget,
    DatePickerInput,
    ExtraNeedMultipleWidget,
    FamilyUserMultipleWidget,
    MultiDateInput,
    TimePickerInput,
)
from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Fieldset, Layout
from profiles.models import City, FamilyUser

from .models import Activity, AllocationAccount, Course, CoursesInstructors, ExtraNeed, PaySlip


class CourseForm(forms.ModelForm):
    activity = forms.ModelChoiceField(
        label=_("Activity"), queryset=Activity.objects, empty_label=None, widget=ActivityWidget()
    )
    instructors = forms.ModelMultipleChoiceField(
        label=_("Instructors"),
        queryset=FamilyUser.active_objects,
        widget=FamilyUserMultipleWidget()
        # required=True,
    )
    name = forms.CharField(
        label=_("Displayed name (optional)"),
        required=False,
        help_text=_("Displayed on calendar under activity name"),
    )
    number = forms.CharField(label=_("Identifier"), required=True)

    price_description = forms.CharField(
        label=_("Informations about pricing"),
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
    )
    start_date = forms.DateTimeField(
        label=_("Start date"),
        required=True,
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=DatePickerInput(format="%d.%m.%Y"),
        help_text=_("format: dd.mm.yyyy, e.g. 31.07.2016"),
    )
    end_date = forms.DateTimeField(
        label=_("End date"),
        required=True,
        input_formats=["%d.%m.%Y", "%Y-%m-%d"],
        widget=DatePickerInput(format="%d.%m.%Y"),
        help_text=_("format: dd.mm.yyyy, e.g. 31.07.2016"),
    )
    start_time = forms.TimeField(
        label=_("Start time"),
        required=False,
        help_text=_("format: hh:mm, e.g. 17:45"),
    )
    end_time = forms.TimeField(
        label=_("End time"),
        required=False,
        help_text=_("format: hh:mm, e.g. 17:45"),
    )
    extra = forms.ModelMultipleChoiceField(
        queryset=ExtraNeed.objects.all(),
        label=_("Extra questions"),
        required=False,
        widget=ExtraNeedMultipleWidget(),
    )
    local_city_override = forms.ModelMultipleChoiceField(
        queryset=City.objects.all(),
        widget=CityMultipleWidget(),
        required=False,
        label=_("Local city override"),
    )

    class Meta:
        model = Course
        fields = (
            "course_type",
            "activity",
            "name",
            "number",
            "instructors",
            "local_city_override",
            "price",
            "price_family",
            "price_local_family",
            "price_local",
            "price_description",
            "number_of_sessions",
            "day",
            "start_date",
            "end_date",
            "start_time",
            "end_time",
            "start_time_mon",
            "end_time_mon",
            "start_time_tue",
            "end_time_tue",
            "start_time_wed",
            "end_time_wed",
            "start_time_thu",
            "end_time_thu",
            "start_time_fri",
            "end_time_fri",
            "start_time_sat",
            "end_time_sat",
            "start_time_sun",
            "end_time_sun",
            "place",
            "min_participants",
            "max_participants",
            "schoolyear_min",
            "schoolyear_max",
            "age_min",
            "age_max",
            "comments",
            "uptodate",
            "announced_js",
            "visible",
            "extra",
        )
        widgets = {
            "place": forms.Textarea(attrs={"rows": 3}),
        }

    class Media:
        js = (
            "js/vendor/moment-with-locales.min.js",
            "js/backend/course-form.js",
        )

    def _filter_limitations(self):
        if settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR:
            self.fields.pop("age_min")
            self.fields.pop("age_max")
            self.fields["schoolyear_min"].required = True
            self.fields["schoolyear_max"].required = True
        else:
            self.fields.pop("schoolyear_min")
            self.fields.pop("schoolyear_max")
            self.fields["age_min"].required = True
            self.fields["age_max"].required = True

    def _filter_price_field(self):
        if settings.KEPCHUP_NO_PAYMENT:
            self.fields.pop("price")
        else:
            self.fields["price"].required = True
        if not settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            self.fields.pop("local_city_override")
            self.fields.pop("price_family")
            self.fields.pop("price_local_family")
            self.fields.pop("price_local")
        else:
            self.fields["price"].label = _("Price for external people")
            self.fields["price_family"].required = True
            self.fields["price_local_family"].required = True
            self.fields["price_local"].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.save()
        for instructor in self.cleaned_data["instructors"]:
            CoursesInstructors.objects.get_or_create(course=instance, instructor=instructor)
        CoursesInstructors.objects.filter(course=instance).exclude(
            instructor__in=self.cleaned_data["instructors"]
        ).delete()
        if instance.is_camp and not settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            delta = instance.end_date - instance.start_date
            dates = []
            for i in range(delta.days + 1):
                dates.append(instance.start_date + datetime.timedelta(days=i))
            for session in instance.get_sessions():
                if session.date not in dates:
                    session.delete()
            for date in dates:
                instance.add_session(date=date)
        return instance

    def pop_initial(self):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pop_initial()
        self.fields["local_city_override"].help_text = _("If empty will use: %s") % ", ".join(
            settings.KEPCHUP_LOCAL_ZIPCODES
        )
        self._filter_limitations()
        self._filter_price_field()
        self.helper = FormHelper()
        self.helper.form_tag = False
        if settings.KEPCHUP_USE_DIFFERENTIATED_PRICES:
            pricing_section = [
                "local_city_override",
                Div(
                    Div("price", css_class="col-md-6"),
                    Div("price_local", css_class="col-md-6"),
                    Div("price_family", css_class="col-md-6"),
                    Div("price_local_family", css_class="col-md-6"),
                    css_class="row",
                ),
                "price_description",
            ]
        else:
            pricing_section = [
                "price",
                "price_description",
            ]
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            dates_section = ["session_dates"]
        else:
            dates_section = [
                Div(
                    Div("number_of_sessions", css_class="col-md-6"),
                    Div("day", css_class="col-md-6"),
                    css_class="course-visible camp-hidden multicourse-hidden row",
                ),
                Div(
                    Div("start_date", css_class="col-md-6"),
                    Div("end_date", css_class="col-md-6"),
                    css_class="row",
                ),
            ]
        dates_section += [
            Div(
                Div(
                    AppendedText("start_time", '<span class="icon-clock"></span>'),
                    css_class="col-md-6",
                ),
                Div(
                    AppendedText("end_time", '<span class="icon-clock"></span>'),
                    css_class="col-md-6",
                ),
                css_class="course-visible camp-hidden multicourse-hidden row",
            ),
            Div(
                HTML("<h4>{}:</h4>".format(_("Daily start and end times"))),
                Div(
                    Div("start_time_mon", css_class="col-md-6"),
                    Div("end_time_mon", css_class="col-md-6"),
                    Div("start_time_tue", css_class="col-md-6"),
                    Div("end_time_tue", css_class="col-md-6"),
                    Div("start_time_wed", css_class="col-md-6"),
                    Div("end_time_wed", css_class="col-md-6"),
                    Div("start_time_thu", css_class="col-md-6"),
                    Div("end_time_thu", css_class="col-md-6"),
                    Div("start_time_fri", css_class="col-md-6"),
                    Div("end_time_fri", css_class="col-md-6"),
                    Div("start_time_sat", css_class="col-md-6"),
                    Div("end_time_sat", css_class="col-md-6"),
                    Div("start_time_sun", css_class="col-md-6"),
                    Div("end_time_sun", css_class="col-md-6"),
                    css_class="row",
                ),
                css_class="multicourse-visible camp-hidden course-hidden",
            ),
        ]

        self.helper.layout = Layout(
            Div(
                Div("course_type", css_class="col-md-6"),
                css_class="row",
            ),
            Div(
                Div("activity", css_class="col-md-6"),
                Div("instructors", css_class="col-md-6"),
                Div("number", css_class="col-md-6"),
                settings.KEPCHUP_CALENDAR_DISPLAY_COURSE_NAMES
                and Div("name", css_class="col-md-6")
                or HTML(""),
                css_class="row",
            ),
            not settings.KEPCHUP_NO_PAYMENT
            and Fieldset(
                _("Pricing"),
                *pricing_section,
            )
            or HTML(""),
            Fieldset(
                _("Dates"),
                *dates_section,
            ),
            "place",
            "comments",
            Fieldset(
                _("Participants and limitations"),
                Div(
                    Div("min_participants", css_class="col-md-6"),
                    Div("max_participants", css_class="col-md-6"),
                    css_class="row",
                ),
                settings.KEPCHUP_LIMIT_BY_SCHOOL_YEAR
                and Div(
                    Div("schoolyear_min", css_class="col-md-6"),
                    Div("schoolyear_max", css_class="col-md-6"),
                    css_class="row",
                )
                or HTML(""),
                settings.KEPCHUP_LIMIT_BY_AGE
                and Div(
                    Div("age_min", css_class="col-md-6"),
                    Div("age_max", css_class="col-md-6"),
                    css_class="row",
                )
                or HTML(""),
            ),
            not settings.KEPCHUP_NO_EXTRAS and ExtraNeed.objects.exists() and "extra" or HTML(""),
            Fieldset(
                _("Management"),
                "uptodate",
                "visible",
                Div("announced_js", css_class="camp-hidden course-show"),
            ),
        )


class MultipleDatesField(forms.CharField):
    date_format = "%d.%m.%Y"
    separator = ","
    widget = MultiDateInput()

    def widget_attrs(self, widget):
        attrs = super(MultipleDatesField, self).widget_attrs(widget)
        attrs.update({"format": self.date_format})
        return attrs

    def to_python(self, value):
        try:
            output = [
                datetime.datetime.strptime(val, self.date_format).date()
                for val in value.split(self.separator)
            ]
        except (ValueError, TypeError):
            raise ValidationError(_("One of the dates is invalid"), code="invalid")
        return output


class ExplicitDatesCourseForm(CourseForm):
    session_dates = MultipleDatesField(
        label=_("Session dates"),
        help_text=_("Separated by commas, e.g. 31.07.2019,22.08.2019"),
    )

    class Meta:
        model = Course
        fields = (
            "course_type",
            "activity",
            "name",
            "number",
            "instructors",
            "local_city_override",
            "price",
            "price_family",
            "price_local_family",
            "price_local",
            "price_description",
            "start_time",
            "end_time",
            "start_time_mon",
            "end_time_mon",
            "start_time_tue",
            "end_time_tue",
            "start_time_wed",
            "end_time_wed",
            "start_time_thu",
            "end_time_thu",
            "start_time_fri",
            "end_time_fri",
            "start_time_sat",
            "end_time_sat",
            "start_time_sun",
            "end_time_sun",
            "place",
            "comments",
            "min_participants",
            "max_participants",
            "schoolyear_min",
            "schoolyear_max",
            "age_min",
            "age_max",
            "uptodate",
            "announced_js",
            "visible",
            "extra",
        )
        widgets = {
            "start_time_mon": TimePickerInput(format="%H:%M"),
            "end_time_mon": TimePickerInput(format="%H:%M"),
            "start_time_tue": TimePickerInput(format="%H:%M"),
            "end_time_tue": TimePickerInput(format="%H:%M"),
            "start_time_wed": TimePickerInput(format="%H:%M"),
            "end_time_wed": TimePickerInput(format="%H:%M"),
            "start_time_thu": TimePickerInput(format="%H:%M"),
            "end_time_thu": TimePickerInput(format="%H:%M"),
            "start_time_fri": TimePickerInput(format="%H:%M"),
            "end_time_fri": TimePickerInput(format="%H:%M"),
            "start_time_sat": TimePickerInput(format="%H:%M"),
            "end_time_sat": TimePickerInput(format="%H:%M"),
            "start_time_sun": TimePickerInput(format="%H:%M"),
            "end_time_sun": TimePickerInput(format="%H:%M"),
            "place": forms.Textarea(attrs={"rows": 3}),
        }

    def pop_initial(self):
        self.fields.pop("start_date")
        self.fields.pop("end_date")

    def __init__(self, *args, **kwargs):
        if "instance" in kwargs and kwargs["instance"]:
            if "initial" not in kwargs:
                kwargs["initial"] = {}
            kwargs["initial"]["session_dates"] = ",".join(
                [
                    session.date.strftime("%d.%m.%Y")
                    for session in kwargs["instance"].get_sessions()
                ]
            )
        super().__init__(*args, **kwargs)

    def clean_session_dates(self):
        dates = self.cleaned_data["session_dates"]
        if not self.cleaned_data["course_type"] == "multicourse":
            return dates
        for session_date in dates:
            day = session_date.isoweekday()
            if day == 1 and not (
                self.cleaned_data.get("start_time_mon") and self.cleaned_data.get("end_time_mon")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for mondays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 2 and not (
                self.cleaned_data.get("start_time_tue") and self.cleaned_data.get("end_time_tue")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for tuesdays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 3 and not (
                self.cleaned_data.get("start_time_wed") and self.cleaned_data.get("end_time_wed")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for wednesdays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 4 and not (
                self.cleaned_data.get("start_time_thu") and self.cleaned_data.get("end_time_thu")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for thursdays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 5 and not (
                self.cleaned_data.get("start_time_fri") and self.cleaned_data.get("end_time_fri")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for fridays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 6 and not (
                self.cleaned_data.get("start_time_sat") and self.cleaned_data.get("end_time_sat")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for saturdays")
                    % session_date.strftime("%d.%m.%Y")
                )
            if day == 7 and not (
                self.cleaned_data.get("start_time_sun") and self.cleaned_data.get("end_time_sun")
            ):
                raise ValidationError(
                    _("%s is invalid as start and end times are not set for sundays")
                    % session_date.strftime("%d.%m.%Y")
                )
        return dates

    def save(self, commit=True):
        instance = super(ExplicitDatesCourseForm, self).save(commit=False)

        dates = self.cleaned_data["session_dates"]
        for session in instance.get_sessions():
            if session.date not in dates:
                session.delete()
        for date in dates:
            instance.add_session(date=date)
        return instance


class ActivityForm(forms.ModelForm):
    number = forms.CharField(label=_("Identifier"), required=True)

    class Meta:
        model = Activity
        fields = ("type", "name", "number", "description", "informations", "allocation_account")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if len(settings.KEPCHUP_ACTIVITY_TYPES) == 1:
            self.fields["type"].widget = forms.HiddenInput()
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "type",
            "name",
            "number",
            settings.KEPCHUP_ENABLE_ALLOCATION_ACCOUNTS and "allocation_account" or None,
            "description",
            "informations",
        )


class AllocationAccountForm(forms.ModelForm):
    class Meta:
        model = AllocationAccount
        fields = ("account", "name")

    def __init__(self, *args, **kwargs):
        super(AllocationAccountForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "account",
            "name",
        )


class PaySlipForm(forms.ModelForm):
    class Meta:
        model = PaySlip
        fields = ("function", "rate_mode", "rate", "start_date", "end_date")
        widgets = {"rate": TextInput}

    def __init__(self, *args, **kwargs):
        super(PaySlipForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
