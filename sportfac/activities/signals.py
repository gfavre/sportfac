from typing import Any

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db import connection
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from absences.models import Session
from profiles.utils import invalidate_user_cache

from .models import Activity
from .models import Course
from .models import CoursesInstructors


FRAGMENT_NAME_COURSE_DETAILS = "course_details"


def invalidate_course_data(pk):
    tenant_pk = connection.get_tenant().pk
    cache_key = f"tenant_{tenant_pk}_course_{pk}"
    cache.delete(cache_key)


def invalidate_course_fragment(course_id: int) -> None:
    """
    Invalidate the template fragment cache for a given course.

    Args:
        course_id: Primary key of the Course instance.
    """
    key = make_template_fragment_key(FRAGMENT_NAME_COURSE_DETAILS, [course_id])
    cache.delete(key)


@receiver([post_save, post_delete], sender=Course)
@receiver([post_save, post_delete], sender=Activity)
def clear_activities_cache(sender, **kwargs):
    cache.delete("activities_context_data")


@receiver([post_save, post_delete], sender=CoursesInstructors)
def invalidate_is_instructor_cache(sender, instance, **kwargs):
    if instance.instructor_id:
        invalidate_user_cache(instance.instructor_id, "is_instructor")
    if instance.course_id:
        invalidate_course_fragment(instance.course_id)


@receiver(post_save, sender=Course, dispatch_uid="course_details_post_save")
def course_post_save_invalidate_cache(sender, instance, **kwargs: Any) -> None:
    """
    Invalidate cache when a Course is created/updated.

    Args:
        sender: Signal sender (Course).
        instance: Saved Course instance.
        **kwargs: Extra signal arguments.
    """
    invalidate_course_fragment(instance.pk)
    invalidate_course_data(instance.id)


@receiver(post_delete, sender=Course, dispatch_uid="course_details_post_delete")
def course_post_delete_invalidate_cache(sender, instance, **kwargs: Any) -> None:
    """
    Invalidate cache when a Course is deleted.

    Args:
        sender: Signal sender (Course).
        instance: Deleted Course instance.
        **kwargs: Extra signal arguments.
    """
    invalidate_course_fragment(instance.pk)
    invalidate_course_data(instance.id)


@receiver([post_save, post_delete], sender=Session)
def invalidate_course_on_session_change(sender, instance, **kwargs):
    """Invalidate course cache whenever a Session changes."""
    if instance.course_id:
        invalidate_course_fragment(instance.course_id)
        invalidate_course_data(instance.course_id)
