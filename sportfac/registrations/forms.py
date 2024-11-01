from django import forms
from django.conf import settings
from django.forms import widgets
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from bootstrap_datepicker_plus.widgets import DatePickerInput
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Div, Field, Fieldset, Layout

from activities.models import Course
from backend.forms import BuildingWidget, CourseWidget, FamilyUserWidget, TeacherWidget, TransportWidget
from profiles.models import FamilyUser, School, SchoolYear
from schools.models import Building, Teacher
from .models import Bill, Child, ExtraInfo, Registration, RegistrationValidation, Transport


AVAILABLE_PAYMENT_METHODS = [
    (method, label)
    for (method, label) in Bill.METHODS
    if method in settings.KEPCHUP_ALTERNATIVE_PAYMENT_METHODS_FROM_BACKEND or method == settings.KEPCHUP_PAYMENT_METHOD
]


class StaticTextWidget(widgets.Widget):
    """
    A custom widget to display static text in a form, styled using Bootstrap's 'form-control-plaintext'.
    """

    def __init__(self, text=None, attrs=None):
        super().__init__(attrs)
        self.text = text

    def render(self, name, value, attrs=None, renderer=None):
        # Build the final attributes using the provided attributes
        final_attrs = self.build_attrs(attrs, extra_attrs={"class": "form-control-static"})
        display_text = self.text if self.text else value
        return f"<p {self._flat_attrs(final_attrs)}>{display_text}</p>"

    def value_from_datadict(self, data, files, name):
        # Returning None to ensure this widget does not alter form data
        return None

    def _flat_attrs(self, attrs):
        """
        Converts dictionary of attributes into a single string.
        """
        return "".join([f' {key}="{value}"' for key, value in attrs.items() if value is not None])


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
    sorting = forms.CharField(required=False, widget=forms.HiddenInput())

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
            "sorting",
            ButtonHolder(
                HTML(
                    f"""
                <button type="submit" class="btn btn-primary btn-large export-button" name="action" value="export" >
                  <i class="icon-file-excel"></i> {submit_label}
                </button>"""
                ),
            ),
        )


class ExtraInfoForm(forms.ModelForm):
    id = forms.CharField(required=False, widget=forms.HiddenInput())

    class Media:
        js = ("js/extra/extra.js",)  # Include the JS file in form's media
        css = {
            "all": ["css/extra/extra.css"],
        }  # Include the JS file in form's media

    class Meta:
        model = ExtraInfo
        fields = ("id", "registration", "key", "value", "image")
        widgets = {
            "registration": StaticTextWidget(),
            "key": forms.HiddenInput(),
            "image": forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)

        if instance and instance.key:
            question = instance.key
            self._handle_initial_value(instance, question)
            self._handle_base_fields(instance, question)
            self._handle_choices(question)
            self._handle_image_field(instance, question)
            if instance.pk:
                self.fields["id"].initial = instance.pk  # Set the initial value of the hidden ID field

        # Initialize the form layout with Crispy Forms
        self._initialize_helper()

    def _handle_initial_value(self, instance, question):
        if not (question.is_choices or question.is_image):
            return
        truthy_values = ["True", "true", "YES", "Yes", "yes", "OUI", "Oui", "oui", "1"]
        falsy_values = ["False", "false", "NO", "No", "no", "NON", "Non", "non", "0"]

        # Set the initial value for the `value` field
        if instance.value == "0":
            self.initial["value"] = next((choice for choice in instance.key.choices if choice in falsy_values), "0")
        elif instance.value == "1":
            self.initial["value"] = next((choice for choice in instance.key.choices if choice in truthy_values), "1")

    def _handle_base_fields(self, instance, question):
        self.fields["registration"].label = ""  # No label for the registration field
        self.fields["registration"].widget = StaticTextWidget(text=str(instance.registration))  # Static text widget
        self.fields["registration"].required = False  # Make the field not required since it's static
        self.fields["value"].label = question.question_label

    def _handle_choices(self, question):
        # Set up choices if the question involves choices
        if question.is_choices:
            choices = question.choices
            if isinstance(choices, list) and all(isinstance(choice, str) for choice in choices):
                choices = [(choice, choice) for choice in choices]  # Convert to (value, label) tuples
            choices.insert(0, ("", _("Please choose")))  # Add a default "please choose" option
            self.fields["value"].widget = forms.widgets.Select(choices=choices)
            self.fields["value"].required = True

    def _handle_image_field(self, instance, question):
        # Set up image field handling
        unique_identifier = f"q-{question.pk}-reg-{instance.registration.pk}"
        if question.is_image:
            self.fields["value"].widget.attrs.update({"data-value-field": unique_identifier})
            if question.image_label:
                self.fields["image"].label = question.image_label
            self.fields["image"].widget.attrs.update({"data-image-field": unique_identifier})
            self.fields["image"].required = True
            if instance.image:
                image_url = instance.image.url
                self.image_div = self._build_image_field_with_preview(unique_identifier, image_url)
            else:
                self.image_div = self._build_image_field(unique_identifier)
        else:
            self.fields.pop("image")  # Remove the image field if it's not needed

    def _build_image_field(self, unique_identifier):
        # Build the image input field layout using Crispy Forms
        drag_and_drop_label = _("Drag & drop or click to upload an image")
        return Div(
            Field(
                "image",
                css_class="file-input",
                style="display:none;",
                **{"data-file-input": unique_identifier},
            ),
            Div(
                HTML(
                    f"""
                    <div class="drop-area" data-drop-area="{unique_identifier}">
                        {drag_and_drop_label}
                        <img data-image-preview="{unique_identifier}" class="image-preview"
                            style="display:none;" alt="Image Preview">
                    </div>
                    """
                ),
                css_class="form-group",
            ),
            css_class="form-group image-drop-container",
        )

    def _build_image_field_with_preview(self, unique_identifier, image_url):
        # Display the drop area and show the existing image with a preview
        label = _("Drag & drop or click to upload and modify current image")
        return Div(
            Field(
                "image",
                css_class="file-input",
                style="display:none;",
                **{"data-file-input": unique_identifier},
            ),
            Div(
                HTML(
                    f"""
                       <div class="drop-area" data-drop-area="{unique_identifier}">
                           {label}
                           <img src="{image_url}" data-image-preview="{unique_identifier}" class="image-preview"
                               style="display:block;" alt="Image Preview">
                       </div>
                       """
                ),
                css_class="form-group",
            ),
            css_class="form-group image-drop-container",
        )

    def _initialize_helper(self):
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.include_media = False
        api_url = reverse("api:api-extra-infos-list")
        self.helper.attrs = {"data-api-url": api_url}
        # Layout includes the dynamic image div if it's set
        self.helper.layout = Layout(
            "id",
            "registration",
            "key",
            "value",
            getattr(self, "image_div", HTML("")),  # Add the image div only if it's been set
        )


class RegistrationVvalidationBaseForm(forms.ModelForm):
    class Media:
        js = ("js/registration-validation-form.js",)
        css = {"all": ("css/registration-validation-form.css",)}

    class Meta:
        model = RegistrationValidation
        fields = ["consent_given"]

    def __init__(self, *args, **kwargs):
        tooltip_message = kwargs.pop("tooltip_message", _("You must tick this box to continue."))
        previous_url = kwargs.pop("previous_url", "#")
        previous_label = kwargs.pop("previous_label", _("Previous"))
        next_url = kwargs.pop("next_url", ".")
        next_label = kwargs.pop("next_label", _("Next"))
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = next_url
        self.helper.attrs = {
            "id": "registration-validation-form",
            "data-tooltip-message": tooltip_message,  # Set the tooltip message as a data attribute
        }
        self.helper.include_media = False
        self.helper.layout = Layout(
            "consent_given",
            HTML(
                f"""
                           <nav style="margin-top: 1.5em;">
                             <ul class="pager" style="font-size: 1.25em;">
                               <li class="previous">
                                 <a href="{previous_url}">
                                   <span aria-hidden="true">←</span> {previous_label}
                                 </a>
                               </li>
                               <li class="next">
                                 <button type="submit" class="btn btn-primary" style="font-size: 1.25em;">
                                   <strong>{next_label} <span aria-hidden="true">→</span></strong>
                                 </button>
                               </li>
                             </ul>
                           </nav>
                           """
            ),
        )


class RegistrationValidationFreeForm(RegistrationVvalidationBaseForm):
    class Meta:
        model = RegistrationValidation
        fields = ["consent_given"]
        labels = {"consent_given": _("I consent to these registrations and to the terms and conditions.")}


class RegistrationValidationForm(RegistrationVvalidationBaseForm):
    class Meta:
        model = RegistrationValidation
        fields = ["consent_given"]
        labels = {
            "consent_given": _(
                "I consent to these registrations and agree to pay the indicated amount "
                "for these registrations to become effective."
            )
        }
