import base64
import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.db import connection
from django.db import transaction
from dynamic_preferences.registries import global_preferences_registry

from registrations.models import ChildActivityLevel
from registrations.models import Registration

from .models import Diploma
from .models import DiplomaBatch
from .models import DiplomaEvent
from .models import DiplomaSupplement


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
            diploma.evaluation = f"{diploma.activity} — {level}"
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
    for course in data["courses"].select_related("activity").prefetch_related("instructors", "participants__child"):
        levels = dict(
            ChildActivityLevel.objects.filter(activity_id=course.activity_id).values_list("child_id", "after_level")
        )
        for registration in course.participants.all():
            child = registration.child
            level = levels.get(child.pk, "")
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
                    evaluation=f"{course.activity.name} — {level}" if level else "",
                    place=data["place"] or str(course.place),
                    instructors=", ".join(person.get_full_name() for person in course.instructors.all()),
                )
            )
    Diploma.objects.bulk_create(diplomas)
    if data.get("supplement"):
        add_supplement(batch, data["supplement"])
    DiplomaEvent.objects.create(batch=batch, actor=actor, action="created", detail="Préparation des diplômes")
    return batch
