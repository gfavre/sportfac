from django import forms
from django.conf import settings
from django.core.mail import EmailMessage
from django.template import loader
from django.utils.safestring import mark_safe

from backend.dynamic_preferences_registry import global_preferences_registry
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Fieldset, Layout, Submit


FORM_TYPES = [
    ("Déposer un témoignage", "Déposer un témoignage"),
    ("Informer l'école", "Informer l'école"),
    ("Chercher de l'aide", "Chercher de l'aide"),
    ("Autre", "Autre"),
]
SCHOOL_YEARS = [
    ("9e", "9e"),
    ("10e", "10e"),
    ("11e", "11e"),
    ("Rac", "Rac"),
    ("Accueil", "Accueil"),
]


class WhistleForm(forms.Form):
    context = forms.CharField(label="", widget=forms.Textarea(), required=True)
    form_type = forms.ChoiceField(label="", choices=FORM_TYPES, required=True)

    other_type = forms.CharField(label="Autre", required=False)
    school_year = forms.ChoiceField(label="Année scolaire", required=False, choices=SCHOOL_YEARS)
    age = forms.IntegerField(label="Âge", required=False)

    email = forms.EmailField(label="E-mail", widget=forms.EmailInput(), required=False)
    phone = forms.CharField(label="Téléphone", required=False)

    def send_mail(self, fail_silently=False):
        preferences = global_preferences_registry.manager()
        from_email = preferences["email__FROM_MAIL"]
        body_tmpl = loader.get_template("nyonmarens/whistle_email.txt")
        context = {
            "context": mark_safe(self.cleaned_data["context"]),
            "form_type": mark_safe(self.cleaned_data["form_type"]),
            "form_type_other": mark_safe(self.cleaned_data["other_type"]),
            "school_year": mark_safe(self.cleaned_data["school_year"]),
            "age": mark_safe(self.cleaned_data["age"]),
            "email": mark_safe(self.cleaned_data["email"]),
            "phone": mark_safe(self.cleaned_data["phone"]),
        }
        email = EmailMessage(
            subject="Formulaire d'annonce de situation - EPS Nyon-Marens",
            body=body_tmpl.render(context),
            from_email=from_email,
            to=settings.KEPCHUP_NYON_MARENS_EMAIL_RECIPIENTS,
        )
        email.send(fail_silently=fail_silently)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "1. Qu'est-ce qui s'est passé ? *",
                Field("context", rows=6),
            ),
            Fieldset(
                "2. En remplissant ce formulaire, tu souhaites",
                "form_type",
                Div(
                    Field("other_type", label=""),
                    css_id="other_type_div",
                ),
            ),
            Fieldset(
                "3. Informations facultatives",
                "school_year",
                "age",
            ),
            Fieldset(
                "4. À remplir uniquement si tu souhaites être contacté pour un échange",
                "email",
                "phone",
            ),
            FormActions(
                Submit("submit", "Envoyer"),
            ),
        )
