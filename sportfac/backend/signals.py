from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from backend.models import YearTenant  # Update this import path as needed


@receiver([post_save, post_delete], sender=YearTenant)
def clear_tenants_cache(sender, **kwargs):
    """
    Clear all cached tenants_context entries when a YearTenant is created, updated, or deleted.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    # Iterate over user IDs in cache (simple version: clear all matching keys)
    # Note: this assumes a predictable cache key pattern
    for user in User.objects.all().only("id"):
        cache_key = f"tenants_context_user_{user.id}"
        cache.delete(cache_key)
