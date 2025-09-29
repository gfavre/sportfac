from django.core.cache import cache
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.models import YearTenant


def _invalidate_all_tenant_caches():
    # ⚠️ selon backend, si Redis -> tu peux utiliser cache.delete_pattern
    cache.delete_pattern("tenants_context_user_*")


@receiver([post_save, post_delete], sender=YearTenant)
def clear_tenant_cache(sender, **kwargs):
    _invalidate_all_tenant_caches()
