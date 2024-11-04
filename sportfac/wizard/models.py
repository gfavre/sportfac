from django.core.cache import cache
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import gettext_lazy as _
from django.utils.text import slugify

from ckeditor_uploader.fields import RichTextUploadingField
from django_tenants.urlresolvers import reverse_lazy

from sportfac.models import TimeStampedModel


class WizardStep(TimeStampedModel):
    STEP_TYPE_CHOICES = [
        ("always", "Always visible"),
        ("conditional", "Visible based on conditions"),
    ]

    title = models.CharField(max_length=50)
    subtitle = models.CharField(max_length=50, blank=True)
    lead = models.CharField(max_length=255, blank=True)
    link_display = models.CharField(max_length=50, blank=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)

    position = models.PositiveIntegerField(default=0, blank=False, null=False)
    description = RichTextUploadingField(blank=True, null=True)

    is_required = models.BooleanField(default=True, verbose_name="Is this step required?")
    step_type = models.CharField(max_length=20, choices=STEP_TYPE_CHOICES, default="always", verbose_name="Step Type")

    display_in_navigation = models.BooleanField(default=True, verbose_name=_("Display in navigation"))
    editable_in_backend = models.BooleanField(
        default=True,
        verbose_name="Is this step editable in the backend?",
    )
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

    def url(self):
        return reverse_lazy("wizard:step", kwargs={"step_slug": self.slug})

    def __str__(self):
        return self.title


# Clear the cache for all wizard steps and individual step cache
def clear_wizard_step_cache(instance=None):
    cache.delete("all_wizard_steps")  # Invalidate all steps cache

    if instance:
        cache_key = f"wizard_step_{instance.slug}"
        cache.delete(cache_key)  # Invalidate the cache for the individual step


@receiver(post_save, sender=WizardStep)
def clear_wizard_step_cache_on_save(sender, instance, **kwargs):
    clear_wizard_step_cache(instance)


@receiver(post_delete, sender=WizardStep)
def clear_wizard_step_cache_on_delete(sender, instance, **kwargs):
    clear_wizard_step_cache(instance)
