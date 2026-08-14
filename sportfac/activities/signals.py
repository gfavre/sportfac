from typing import Any

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.db import connection
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from absences.models import Session
from profiles.utils import invalidate_user_cache
from waiting_slots.models import WaitingSlot

from .cache import get_structural_activities_cache_key
from .models import Activity
from .models import Course
from .models import CoursesInstructors


FRAGMENT_NAME_COURSE_DETAILS = "course_details"

# Fields that change on every registration/waiting-slot action but aren't part of what
# ActivityViewSet's structural cache serves (see api.views.activities_views and
# CourseInlineSerializer) - a save touching only these must not invalidate that cache, or it
# would get busted on nearly every write during a registration rush, defeating its purpose.
NON_STRUCTURAL_COURSE_FIELDS = frozenset({"nb_participants", "has_waiting_list", "places_available_reminder_sent_on"})


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


def invalidate_activities_structural_cache():
    tenant_pk = connection.get_tenant().pk
    cache.delete(get_structural_activities_cache_key(tenant_pk))


@receiver(post_save, sender=Course, dispatch_uid="invalidate_activities_structural_cache_on_course_save")
def invalidate_structural_cache_on_course_save(sender, instance, update_fields, **kwargs):
    if update_fields is not None and set(update_fields) <= NON_STRUCTURAL_COURSE_FIELDS:
        return
    invalidate_activities_structural_cache()


@receiver(post_delete, sender=Course, dispatch_uid="invalidate_activities_structural_cache_on_course_delete")
def invalidate_structural_cache_on_course_delete(sender, instance, **kwargs):
    invalidate_activities_structural_cache()


@receiver(
    [post_save, post_delete], sender=Activity, dispatch_uid="invalidate_activities_structural_cache_on_activity_change"
)
def invalidate_structural_cache_on_activity_change(sender, instance, **kwargs):
    invalidate_activities_structural_cache()


@receiver(
    [post_save, post_delete], sender=Session, dispatch_uid="invalidate_activities_structural_cache_on_session_change"
)
def invalidate_structural_cache_on_session_change(sender, instance, **kwargs):
    invalidate_activities_structural_cache()


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


@receiver([post_save, post_delete], sender=WaitingSlot)
def update_course_waiting_list_flag(sender, instance, **kwargs):
    course = instance.course
    has_waiting = course.waiting_slots.exists()
    if course.has_waiting_list != has_waiting:
        course.has_waiting_list = has_waiting
        course.save(update_fields=["has_waiting_list"])
