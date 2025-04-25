from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Activity, Course  # adapte les imports si besoin


@receiver([post_save, post_delete], sender=Course)
@receiver([post_save, post_delete], sender=Activity)
def clear_activities_cache(sender, **kwargs):
    cache.delete("activities_context_data")
