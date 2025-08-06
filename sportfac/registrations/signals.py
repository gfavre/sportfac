from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from profiles.utils import invalidate_user_cache
from .models import Child


@receiver([post_save, post_delete], sender=Child)
def invalidate_updatable_children_cache(sender, instance, **kwargs):
    if instance.family_id:
        invalidate_user_cache(instance.family_id, "updatable_children")
