from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from activities.models import Course
from backend.forms import BuildingWidget, CourseWidget, FamilyUserWidget, TeacherWidget, TransportWidget
from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Fieldset, Layout
from profiles.models import FamilyUser, School, SchoolYear
from schools.models import Building, Teacher

from .models import Bill, Child, Registration, Transport


AVAILABLE_PAYMENT_METHODS = [
    (method, label)
    for (method, label) in Bill.METHODS
    if method in settings.KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND or method == settings.KEPCHUP_PAYMENT_METHOD
]


class EmptyForm(forms.Form):
    pass


class BillForm(forms.ModelForm):
    status = forms.ChoiceField(choices=list(Bill.STATUS)[1:], label=_("Payment status"))
    payment_method = forms.ChoiceField(choices=AVAILABLE_PAYMENT_METHODS, required=False, label=_("Payment method"))
    payment_date = forms.DateTimeField(
        widget=DatePickerInput(format="%d.%m.%Y"), label=_("Payment date"), required=False
    )

    class Meta:
        model = Bill
        fields = ("status", "payment_method")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["payment_date"].initial = self.instance.payment_date or timezone.now()
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.include_media = False

    def clean_payment_date(self):
        payment_date = self.cleaned_data["payment_date"]
        if payment_date and self.cleaned_data["status"] != Bill.STATUS.paid:
            return None
        return payment_date


class ChildForm(forms.ModelForm):
    birth_date = forms.DateTimeField(
        label=_("Birth date"),
        widget=DatePickerInput(format="%d.%m.%Y"),
        help_text=_("Format: 31.12.2012"),
    )
    sex = forms.ChoiceField(label=_("Sex"), widget=forms.widgets.RadioSelect, choices=Child.SEX)
    teacher = forms.ModelChoiceField(
        label=_("Teacher"),
        queryset=Teacher.objects.prefetch_related("years"),
        required=False,
        widget=TeacherWidget,
    )
    building = forms.ModelChoiceField(
        label=_("Building"),
        queryset=Building.objects.all(),
        required=False,
        widget=BuildingWidget,
    )
    nationality = forms.ChoiceField(label=_("Nationality"), choices=Child.NATIONALITY)
    language = forms.ChoiceField(label=_("Language"), choices=Child.LANGUAGE)
    school_year = forms.ModelChoiceField(
        label=_("School year"), queryset=SchoolYear.visible_objects.all(), required=False
    )
    family = forms.ModelChoiceField(
        label=_("Parent"),
        queryset=FamilyUser.active_objects.all(),
        required=False,
        widget=FamilyUserWidget,
    )
    id_lagapeo = forms.IntegerField(label=_("SSF number"), required=False)

    school = forms.ModelChoiceField(label=_("School"), queryset=School.objects.filter(selectable=True), required=False)
    emergency_number = forms.CharField(label=_("Emergency number"), required=False)
    bib_number = forms.CharField(label=_("Bib number"), required=False)
    avs = forms.CharField(label=_("AVS"), required=False, help_text="756.XXXX.XXXX.XX")

    class Meta:
        model = Child
        fields = (
            "id_lagapeo",
            "family",
            "first_name",
            "last_name",
            "sex",
            "birth_date",
            "nationality",
            "avs",
            "language",
            "school",
            "other_school",
            "school_year",
            "teacher",
            "building",
            "emergency_number",
            "bib_number",
            "is_blacklisted",
        )

    def clean_id_lagapeo(self):
        id_lagapeo = self.cleaned_data["id_lagapeo"]
        if not id_lagapeo:
            return None
        try:
            child = Child.objects.get(id_lagapeo=id_lagapeo)
            if self.instance and self.instance != child:
                raise forms.ValidationError(
                    mark_safe(
                        _(
                            "This identifer is already attributed to another child.<br>"
                            'Please <a href="%s" target="_blank">review and delete the other child account</a>.'
                        )
                        % child.get_backend_detail_url()
                    ),
                    code="unique",
                )
        except Child.DoesNotExist:
            return id_lagapeo
        return id_lagapeo

    def get_submit_button(self):
        return HTML(
            """
                    <button type="submit" class="btn btn-success btn-large" name="action" value="save">
                      <i class="icon-plus"></i> {}
                    </button>
                    """.format(
                _("Create child")
            )
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.KEPCHUP_USE_BUILDINGS:
            del self.fields["building"]
        self.helper = FormHelper()
        self.helper.include_media = False
        self.helper.layout = Layout(
            "family",
            Div(
                Div("first_name", css_class="col-sm-6"),
                Div("last_name", css_class="col-sm-6"),
                css_class="row",
            ),
            "sex",
            Div(
                Div("birth_date", css_class="col-sm-3"),
                css_class="row",
            ),
            Div(
                Div("nationality", css_class="col-sm-6"),
                Div("language", css_class="col-sm-6"),
                css_class="row",
            ),
            "avs",
            settings.KEPCHUP_EMERGENCY_NUMBER_MANDATORY and "emergency_number" or HTML(""),
            settings.KEPCHUP_BIB_NUMBERS and "bib_number" or HTML(""),
            settings.KEPCHUP_USE_BLACKLISTS and "is_blacklisted" or HTML(""),
            Fieldset(
                _("School informations"),
                settings.KEPCHUP_IMPORT_CHILDREN and "id_lagapeo" or HTML(""),
                Div(
                    Div("school_year", css_class="col-sm-6"),
                    settings.KEPCHUP_USE_BUILDINGS and Div("building", css_class="col-sm-6") or HTML(""),
                    settings.KEPCHUP_PREFILL_YEARS_WITH_TEACHERS and Div("teacher", css_class="col-sm-6") or HTML(""),
                    settings.KEPCHUP_CHILD_SCHOOL and Div("school", css_class="col-sm-6") or HTML(""),
                    settings.KEPCHUP_CHILD_SCHOOL and Div("other_school", css_class="col-sm-6") or HTML(""),
                    css_class="row",
                ),
            ),
            ButtonHolder(self.get_submit_button()),
        )


class ChildUpdateForm(ChildForm):
    def get_submit_button(self):
        return HTML(
            """
                    <button type="submit" class="btn btn-success btn-large" name="action" value="save">
                      {}
                    </button>
                    """.format(
                _("Update child")
            )
        )


class RegistrationModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.detailed_label()


class MoveRegistrationsForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(
        queryset=Registration.objects.all(), widget=forms.MultipleHiddenInput
    )
    destination = RegistrationModelChoiceField(
        queryset=Course.objects.all(),
        widget=CourseWidget(),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        course_qs = Course.objects.select_related("activity")
        if user and user.is_restricted_manager:
            course_qs = course_qs.filter(activity__managers=user)
        self.fields["destination"].queryset = course_qs
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class MoveTransportForm(forms.Form):
    registrations = forms.ModelMultipleChoiceField(
        queryset=Registration.objects.all(), widget=forms.MultipleHiddenInput
    )
    destination = forms.ModelChoiceField(queryset=Transport.objects.all(), widget=TransportWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class TransportForm(forms.ModelForm):
    class Meta:
        model = Transport
        fields = ("name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"


class BillExportForm(forms.Form):
    STATUS_CHOICES = [("all", "All"), ("paid", "Paid"), ("waiting", "Waiting")]

    AMOUNT_CHOICES = [("all", "All Amounts"), ("positive", "Amounts > 0"), ("zero", "Amounts = 0")]

    start = forms.DateField(required=False, widget=forms.HiddenInput())
    end = forms.DateField(required=False, widget=forms.HiddenInput())
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False, widget=forms.HiddenInput())
    amount = forms.ChoiceField(choices=AMOUNT_CHOICES, required=False, widget=forms.HiddenInput())

    class Meta:
        # Ensure correct usage of widgets
        fields = ["start", "end", "status", "amount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "export-form"
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        submit_label = _("Export to XLS")
        self.helper.layout = Layout(
            "start",
            "end",
            "status",
            "amount",
            ButtonHolder(
                HTML(
                    f"""
                <button type="submit" class="btn btn-primary btn-large export-button" name="action" value="export" >
                  <i class="icon-file-excel"></i> {submit_label}
                </button>"""
                ),
            ),
        )
