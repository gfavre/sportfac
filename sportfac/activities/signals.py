from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from profiles.utils import invalidate_user_cache
from .models import Activity, Course, CoursesInstructors


@receiver([post_save, post_delete], sender=Course)
@receiver([post_save, post_delete], sender=Activity)
def clear_activities_cache(sender, **kwargs):
    cache.delete("activities_context_data")


@receiver([post_save, post_delete], sender=CoursesInstructors)
def invalidate_is_instructor_cache(sender, instance, **kwargs):
    if instance.instructor_id:
        invalidate_user_cache(instance.instructor_id, "is_instructor")
