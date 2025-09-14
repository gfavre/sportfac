from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

from sportfac.models import TimeStampedModel


EXTRA_TYPES = (("B", _("Boolean")), ("C", _("Characters")), ("I", _("Integer")), ("IM", _("Image")))


class ExtraNeed(TimeStampedModel):
    courses = models.ManyToManyField("Course", related_name="extra", blank=True)

    question_label = models.CharField(max_length=255, verbose_name=_("Question"), help_text=_("e.g. Shoes size?"))
    image_label = models.CharField(
        max_length=255, verbose_name=_("Image label"), help_text=_("if type is image"), blank=True
    )
    extra_info = models.TextField(blank=True)
    mandatory = models.BooleanField(default=True)
    type = models.CharField(verbose_name=_("Type of answer"), choices=EXTRA_TYPES, default="C", max_length=2)
    choices = ArrayField(
        verbose_name=_("Limit to values (internal name, display name),(internal name 2, display name 2)"),
        base_field=models.CharField(max_length=255),
        blank=True,
        null=True,
    )
    price_modifier = ArrayField(
        verbose_name=_("Modify price by xx francs if this value is selected"),
        help_text=_("List of positive/negative values, if boolean: False value then True"),
        base_field=models.IntegerField(),
        blank=True,
        null=True,
    )
    step = models.ForeignKey(
        "wizard.WizardStep",
        verbose_name=_("Wizard step"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    default = models.CharField(verbose_name=_("Default value"), default="", blank=True, max_length=255)

    class Meta:
        verbose_name = _("extra question")
        verbose_name_plural = _("extra questions")

    @property
    def is_boolean(self):
        return self.type == "B"

    @property
    def is_characters(self):
        return self.type == "C"

    @property
    def is_choices(self):
        return len(self.choices) > 0

    @property
    def is_integer(self):
        return self.type == "I"

    @property
    def is_image(self):
        return self.type == "IM"

    @property
    def price_dict(self):
        if not self.price_modifier:
            return {}
        if self.is_image or self.is_boolean:
            return dict(zip(("0", "1"), self.price_modifier))
        return dict(zip(self.choices, self.price_modifier))

    def __str__(self):
        if self.choices:
            out = "{} ({})".format(self.question_label, ", ".join(self.choices))
            if self.price_modifier:
                out += " - (" + ", ".join([str(price) for price in self.price_modifier]) + ")"
            return out
        return self.question_label
