from django import forms
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.translation import gettext_lazy as _

from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from dynamic_preferences.registries import global_preferences_registry


class ContactForm(forms.Form):
    name = forms.CharField(label=_("Name"), widget=forms.TextInput())
    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={
                "placeholder": "john@example.com",
            }
        ),
    )
    subject = forms.CharField(label=_("Subject"), widget=forms.TextInput())

    message = forms.CharField(label=_("Message"), widget=forms.Textarea(attrs={"rows": 5}))
    captcha = ReCaptchaField(widget=ReCaptchaV3, label="")

    def send_mail(self, fail_silently=False):
        global_preferences = global_preferences_registry.manager()

        bcc = None
        if settings.KEPCHUP_SEND_COPY_CONTACT_MAIL_TO_ADMIN:
            bcc = ["%s <%s>" % (mail_tuple[0], mail_tuple[1]) for mail_tuple in settings.MANAGERS]

        email = EmailMessage(
            subject="%s [%s - formulaire de contact]"
            % (
                self.cleaned_data["subject"],
                global_preferences["email__SCHOOL_NAME"],
            ),
            body="%s <%s> a utilisé le formulaire de contact.\n\n %s"
            % (
                self.cleaned_data["name"],
                self.cleaned_data["email"],
                self.cleaned_data["message"],
            ),
            from_email=global_preferences["email__FROM_MAIL"],
            to=[global_preferences["email__CONTACT_MAIL"]],
            bcc=bcc,
            reply_to=["%s <%s>" % (self.cleaned_data["name"], self.cleaned_data["email"])],
        )
        email.send(fail_silently=fail_silently)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.form_group_wrapper_class = "row"
        self.helper.label_class = "col-sm-2"
        self.helper.field_class = "col-sm-10"
        self.helper.include_media = False
        self.helper.form_tag = False
        self.helper.layout = Layout(
            "name",
            "email",
            "subject",
            "message",
            "captcha",
        )
