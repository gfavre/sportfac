from django.db import models
from django.utils.text import slugify

from sportfac.models import TimeStampedModel


class WizardStep(TimeStampedModel):
    STEP_TYPE_CHOICES = [
        ("always", "Always visible"),
        ("conditional", "Visible based on conditions"),
    ]

    title = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    position = models.PositiveIntegerField(default=0, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    is_required = models.BooleanField(default=True, verbose_name="Is this step required?")
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default="always", verbose_name="Step Type")

    condition_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Condition Name",
        help_text="Choose the predefined condition to determine visibility of this step.",
    )
    handler_class = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Handler Class",
        help_text="Define the handler class to be used for this step.",
    )

    class Meta:
        ordering = ["position"]

    def save(self, *args, **kwargs):
        """Automatically generate a slug from the title."""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
