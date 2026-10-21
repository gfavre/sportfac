import mimetypes

from django import forms
from django.utils import timezone

from activities.models import Course
from registrations.levels import level_menu_label

from .models import Diploma
from .models import DiplomaBatch
from .services import EMPTY_LEVEL
from .services import final_level_counts


DEFAULT_MESSAGE = """Madame, Monsieur,

Nous avons le plaisir de vous envoyer le diplôme de participation au sport scolaire facultatif de votre enfant.
Ce document correspond à celui qui lui a été distribué, sous forme papier, lors de la dernière journée.

En restant à votre disposition pour tout complément d’information,
nous vous adressons, Madame, Monsieur, nos cordiaux messages.

Commune de Montreux
Sport scolaire facultatif
Rue du Temple 11
1820 Montreux"""


class BatchForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(label="Cours", queryset=Course.objects.none())
    final_levels = forms.MultipleChoiceField(
        label="Niveaux finaux à inclure",
        widget=forms.CheckboxSelectMultiple,
        help_text="Tous sont cochés par défaut. Décochez les niveaux à exclure, par exemple ABS ou Sans niveau.",
        error_messages={"required": "Sélectionnez au moins un niveau final à inclure."},
    )
    season = forms.CharField(label="Saison / année", max_length=100)
    issued_on = forms.DateField(
        label="Date du diplôme",
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    place = forms.CharField(
        label="Lieu de cours",
        required=False,
        max_length=255,
        help_text="Laissez vide pour reprendre le lieu de chaque cours.",
    )
    subject = forms.CharField(label="Objet du mail", max_length=255)
    message = forms.CharField(label="Texte du mail", widget=forms.Textarea, initial=DEFAULT_MESSAGE)
    supplement = forms.FileField(
        label="Descriptif des niveaux (image ou PDF)",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*,application/pdf"}),
        help_text=(
            "Facultatif : joignez le descriptif des niveaux de ski ou de snowboard. "
            "Image ou PDF, 10 Mo maximum. Il sera joint au mail avec le diplôme, sans conversion."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.all().order_by("number")
        course_ids = (
            self.data.getlist("courses")
            if self.is_bound and hasattr(self.data, "getlist")
            else (self.data.get("courses", []) if self.is_bound else self.initial.get("courses", []))
        )
        course_ids = [str(pk) for pk in course_ids if str(pk).isdigit()]
        self.level_counts = final_level_counts(Course.objects.filter(pk__in=course_ids))
        self.fields["final_levels"].choices = [
            (code, f"{'Sans niveau' if code == EMPTY_LEVEL else level_menu_label(code)} ({count})")
            for code, count in sorted(self.level_counts.items())
        ]
        if not self.is_bound:
            self.initial["final_levels"] = list(self.level_counts)

    def clean(self):
        data = super().clean()
        if data.get("courses") and not self.level_counts:
            raise forms.ValidationError("Aucun enfant inscrit dans les cours sélectionnés.")
        return data

    def clean_supplement(self):
        return validate_supplement(self.cleaned_data.get("supplement"))


def validate_supplement(upload):
    if upload:
        if upload.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Choisissez une image ou un PDF de 10 Mo maximum.")
        content_type = mimetypes.guess_type(upload.name)[0] or ""
        is_pdf = upload.read(5) == b"%PDF-"
        upload.seek(0)
        if not is_pdf and not content_type.startswith("image/"):
            raise forms.ValidationError("Choisissez une image ou un PDF de 10 Mo maximum.")
    return upload


class DiplomaForm(forms.ModelForm):
    class Meta:
        model = Diploma
        fields = ("first_name", "last_name", "evaluation", "place", "instructors")
        labels = {
            "first_name": "Prénom",
            "last_name": "Nom",
            "evaluation": "Texte sur le diplôme",
            "place": "Lieu",
            "instructors": "Prénom du moniteur de la dernière session",
        }
        help_texts = {
            "evaluation": (
                "Texte imprimé dans la rubrique « Évaluation » du diplôme, par exemple : "
                "Ski alpin — niveau 1 acquis. Prérempli à partir du niveau après cours. "
                "Modifier ce texte ne change pas le niveau enregistré dans le suivi de l’enfant."
            ),
        }


class DiplomaMessageForm(forms.ModelForm):
    class Meta:
        model = DiplomaBatch
        fields = ("subject", "message")
        labels = {"subject": "Objet", "message": "Texte du mail"}
