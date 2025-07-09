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
    title = models.CharField(max_length=50, help_text=_("The title is used in navigation and on top of the page"))
    subtitle = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Displayed next to the title, in smaller caps. Not visible in navigation."),
    )
    lead = models.CharField(max_length=255, blank=True, help_text=_("Big text displayed below the title."))
    link_display = models.CharField(max_length=50, blank=True)
    description = RichTextUploadingField(
        blank=True, null=True, help_text=_("Free form description, with images if necessary")
    )

    slug = models.SlugField(
        max_length=50,
        unique=True,
        blank=True,
        help_text=_(
            "Part of the url. Must be unique, and not contain spaces, accentuated letters or special characters."
        ),
    )
    position = models.PositiveIntegerField(default=0, blank=False, null=False)

    display_in_navigation = models.BooleanField(default=True, verbose_name=_("Display in navigation"))
    editable_in_backend = models.BooleanField(
        default=True,
        verbose_name="Is this step editable in the backend?",
    )

    class Meta:
        ordering = ["position"]

    def save(self, *args, **kwargs):
        """Automatically generate a slug from the title."""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def backend_url(self):
        return reverse_lazy("backend:wizard-step-update", kwargs={"slug": self.slug})

    def get_absolute_url(self):
        return reverse_lazy("wizard:step", kwargs={"step_slug": self.slug})

    def url(self):
        return self.get_absolute_url()

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
