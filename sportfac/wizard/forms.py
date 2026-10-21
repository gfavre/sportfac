from django.forms import ModelForm
from django.utils.text import gettext_lazy as _

from .models import WizardStep


class WizardStepForm(ModelForm):
    class Meta:
        model = WizardStep
        fields = ["title", "subtitle", "lead", "link_display", "description", "slug"]
        labels = {
            "title": _("Titre de l’étape"),
            "subtitle": _("Sous-titre"),
            "lead": _("Texte d’introduction"),
            "description": _("Contenu de la page"),
            "link_display": _("Libellé du bouton d’accès à cette étape"),
            "slug": _("Identifiant dans l’URL"),
        }
        help_texts = {
            "title": _("Affiché dans la navigation du parcours et en haut de la page."),
            "subtitle": _("Facultatif. Affiché à côté du titre, uniquement sur la page."),
            "lead": _("Facultatif. Texte mis en évidence sous le titre, avant le contenu."),
            "description": _("Texte affiché avant les champs de l’étape. Images et liens possibles."),
            "link_display": _(
                "Bouton de l’étape précédente menant ici. Laissez vide pour garder le libellé par défaut."
            ),
            "slug": _("Conservez sa valeur habituelle. L’identifiant doit être unique, sans espaces ni accents."),
        }
