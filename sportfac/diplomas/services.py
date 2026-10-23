import base64
import mimetypes
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.db import transaction
from django.db.models import Count
from django.db.models import Max
from django.db.models import OuterRef
from django.db.models import Subquery
from dynamic_preferences.registries import global_preferences_registry

from registrations.levels import diploma_evaluation
from registrations.models import ChildActivityLevel
from registrations.models import Registration

from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .models import DiplomaSupplement


EMPTY_LEVEL = "__empty__"


@transaction.atomic
def separate_draft_courses(batch_id, course_number, actor):
    batch = DiplomaBatch.objects.select_for_update().get(pk=batch_id)
    if batch.status not in ("draft", "ready", "failed") or batch.source_schema != connection.schema_name:
        raise ValueError("Ce groupe ne peut pas être séparé pendant sa génération ou depuis une autre période.")
    if batch.diplomas.exclude(mail_status="pending", published_at__isnull=True).exists():
        raise ValueError("Ce groupe contient déjà des publications ou des envois : il reste inchangé.")
    numbers = set(batch.diplomas.values_list("course_number", flat=True))
    if course_number not in numbers:
        raise ValueError("Ce cours a changé de groupe. Retrouvez-le dans la liste des diplômes.")
    supplements = list(batch.supplements.all())
    for number in sorted(numbers - {course_number}):
        separated = DiplomaBatch.objects.create(
            season=batch.season,
            issued_on=batch.issued_on,
            source_schema=batch.source_schema,
            subject=batch.subject,
            message=batch.message,
            logo=batch.logo,
            created_by=batch.created_by,
        )
        ids = list(batch.diplomas.filter(course_number=number).values_list("pk", flat=True))
        Diploma.objects.filter(pk__in=ids).update(batch=separated)
        DiplomaEvent.objects.filter(diploma_id__in=ids).update(batch=separated)
        DiplomaSupplement.objects.bulk_create(
            [DiplomaSupplement(batch=separated, name=item.name, content=item.content) for item in supplements]
        )
        DiplomaEvent.objects.create(
            batch=separated,
            actor=actor,
            action="created",
            detail=f"Cours {number} séparé du brouillon {batch.pk} ; textes et pièces jointes conservés.",
        )
    if len(numbers) > 1:
        # Invalidate confirmations opened before the course groups changed.
        batch.status = "draft"
        batch.print_pdf = None
        batch.error = ""
        batch.save(update_fields=["status", "print_pdf", "error", "modified"])
        DiplomaEvent.objects.create(
            batch=batch,
            actor=actor,
            action="edited",
            detail=f"Brouillon limité au cours {course_number} ; autres cours séparés.",
        )
    return batch


def course_mail_history(source_schema, course_numbers):
    # Course numbers belong to a period; snapshots remain available after its deletion.
    return list(
        Diploma.objects.filter(
            batch__source_schema=source_schema,
            course_number__in=course_numbers,
            mail_status="sent",
            sent_at__isnull=False,
        )
        .values("course_number", "batch_id", "batch__season")
        .annotate(sent_count=Count("pk"), last_sent=Max("sent_at"))
        .order_by("-last_sent", "course_number")
    )


def final_level_counts(courses):
    levels = ChildActivityLevel.objects.filter(
        child_id=OuterRef("child_id"), activity_id=OuterRef("course__activity_id")
    ).values("after_level")[:1]
    return Counter(
        level or EMPTY_LEVEL
        for level in Registration.objects.filter(course__in=courses)
        .annotate(final_level=Subquery(levels))
        .values_list("final_level", flat=True)
    )


def diploma_logo():
    name = global_preferences_registry.manager()["site__DIPLOMA_LOGO"] or settings.KEPCHUP_DIPLOMA_LOGO
    path = finders.find(name) if name else None
    if not path:
        return ""
    content_type = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{content_type};base64," + base64.b64encode(Path(path).read_bytes()).decode("ascii")


def add_supplement(batch, upload):
    return DiplomaSupplement.objects.create(batch=batch, name=Path(upload.name).name, content=upload.read())


@transaction.atomic
def complete_missing_levels(batch, actor=None):
    batch = DiplomaBatch.objects.select_for_update().defer("print_pdf", "logo").get(pk=batch.pk)
    if batch.status != "draft" or batch.source_schema != connection.schema_name:
        return
    diplomas = list(batch.diplomas.filter(evaluation="", pdf__isnull=True, published_at__isnull=True))
    registrations = dict(
        Registration.objects.filter(pk__in=[d.source_registration_id for d in diplomas]).values_list("pk", "child_id")
    )
    activities = dict(Registration.objects.filter(pk__in=registrations).values_list("pk", "course__activity_id"))
    levels = {
        (child, activity): level
        for child, activity, level in ChildActivityLevel.objects.filter(
            child_id__in=registrations.values(), activity_id__in=activities.values()
        ).values_list("child_id", "activity_id", "after_level")
    }
    changed = []
    for diploma in diplomas:
        level = levels.get(
            (registrations.get(diploma.source_registration_id), activities.get(diploma.source_registration_id))
        )
        if level:
            diploma.level = level
            diploma.evaluation = diploma_evaluation(diploma.activity, level)
            changed.append(diploma)
    if changed:
        Diploma.objects.bulk_update(changed, ["level", "evaluation"])
        DiplomaEvent.objects.bulk_create(
            [
                DiplomaEvent(
                    batch=batch,
                    diploma=d,
                    actor=actor,
                    action="edited",
                    detail="Niveau après cours repris automatiquement",
                )
                for d in changed
            ]
        )


@transaction.atomic
def create_batch(data, actor):
    batch = DiplomaBatch.objects.create(
        season=data["season"],
        issued_on=data["issued_on"],
        source_schema=connection.schema_name,
        subject=data["subject"],
        message=data["message"],
        created_by=actor,
        logo=diploma_logo(),
    )
    diplomas = []
    for course in data["courses"].select_related("activity").prefetch_related("participants__child"):
        last_session = course.sessions.select_related("instructor").order_by("-date").first()
        instructor_name = last_session.instructor.first_name if last_session and last_session.instructor else ""
        levels = dict(
            ChildActivityLevel.objects.filter(activity_id=course.activity_id).values_list("child_id", "after_level")
        )
        for registration in course.participants.all():
            child = registration.child
            level = levels.get(child.pk, "")
            if "final_levels" in data and (level or EMPTY_LEVEL) not in data["final_levels"]:
                continue
            diplomas.append(
                Diploma(
                    batch=batch,
                    parent_id=child.family_id,
                    source_registration_id=registration.pk,
                    first_name=child.first_name,
                    last_name=child.last_name,
                    activity=course.activity.name,
                    course_number=course.number,
                    level=level,
                    evaluation=diploma_evaluation(course.activity.name, level),
                    place=data["place"] or str(course.place),
                    instructors=instructor_name,
                )
            )
    Diploma.objects.bulk_create(diplomas)
    if data.get("supplement"):
        add_supplement(batch, data["supplement"])
    DiplomaEvent.objects.create(batch=batch, actor=actor, action="created", detail="Préparation des diplômes")
    return batch
