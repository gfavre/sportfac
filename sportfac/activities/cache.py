def get_structural_activities_cache_key(tenant_pk):
    """Cache key for the per-tenant, family-independent activities/courses payload.

    Shared by api.views.activities_views.ActivityViewSet (which populates it) and
    activities.signals (which invalidates it), so both sides always agree on the key.
    """
    return f"tenant_{tenant_pk}_activities_structural"
