import unicodedata
from collections import defaultdict

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.timezone import now
from django.utils.translation import gettext as _

from .models import Child
from .models import Registration
from .models import Transport


def _alphabetical(value):
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold()) if not unicodedata.combining(c))


def _assign_missing_bibs(car, passengers, reserved):
    available = iter(
        f"{car.bib_prefix}{rank:02d}" for rank in range(1, 100) if f"{car.bib_prefix}{rank:02d}" not in reserved
    )
    changed = []
    for child in passengers:
        if child.bib_number:
            continue
        number = next(available, None)
        if number is None:
            raise ValidationError(_("Le car %(car)s n’a plus de numéro de dossard disponible.") % {"car": car})
        child.bib_number = number
        reserved.add(number)
        changed.append(child)
    return changed


def _replace_bibs(car, passengers, reserved):
    for rank, child in enumerate(passengers, 1):
        number = f"{car.bib_prefix}{rank:02d}"
        if number in reserved:
            raise ValidationError(_("Un dossard calculé est déjà attribué à un enfant hors de cette génération."))
        child.bib_number = number
        reserved.add(number)
    return passengers


def _group_passengers(children, assignments, transports, errors):
    groups = defaultdict(list)
    for child in children:
        cars = assignments[child.pk]
        if None in cars or len(cars) != 1:
            errors.append(
                {
                    "message": _("%(child)s doit être affecté à un seul car sur toutes ses inscriptions actives.")
                    % {"child": child},
                    "child": child,
                    "kind": "assignment",
                }
            )
            continue
        car = transports[next(iter(cars))]
        groups[car.pk].append(child)
        if car.bib_prefix is None:
            errors.append(
                {
                    "message": _("Le car %(car)s n'a pas de préfixe de dossard.") % {"car": car},
                    "car": car,
                    "kind": "prefix",
                }
            )
    return groups


def _reserve_plan_bibs(children, reserved, errors):
    duplicates = set()
    for child in children:
        number = child.bib_number
        if not number:
            continue
        if number in reserved and number not in duplicates:
            errors.append(
                {
                    "message": _(
                        "Le dossard %(number)s est déjà attribué à plusieurs enfants. "
                        "Corrigez ce doublon avant de continuer."
                    )
                    % {"number": number},
                    "child": child,
                }
            )
            duplicates.add(number)
        reserved.add(number)


def prepare_bibs(*, overwrite=False, lock=False):
    """Build the same plan for preview and generation; never write during preparation."""
    cars_query = Transport.objects.order_by("pk")
    registrations = Registration.objects.order_by("pk")
    children_query = Child.objects.order_by("pk")
    if lock:
        cars_query = cars_query.select_for_update()
        registrations = registrations.select_for_update()
        children_query = children_query.select_for_update()
    transports = {car.pk: car for car in cars_query}
    assignments = defaultdict(set)
    for registration in registrations:
        assignments[registration.child_id].add(registration.transport_id)
    children = list(children_query.filter(pk__in=assignments))
    errors = []
    if not children:
        errors.append({"message": _("Aucun enfant avec une inscription active à numéroter.")})
    groups = _group_passengers(children, assignments, transports, errors)
    existing_count = sum(bool(child.bib_number) for child in children)
    reserved = set(
        Child.objects.exclude(pk__in=assignments).exclude(bib_number="").values_list("bib_number", flat=True)
    )
    if not overwrite:
        _reserve_plan_bibs(children, reserved, errors)
    changed = []
    summaries = []
    assign = _replace_bibs if overwrite else _assign_missing_bibs
    for car_id, passengers in groups.items():
        car = transports[car_id]
        number_range = {f"{car.bib_prefix}{rank:02d}" for rank in range(1, 100)}
        summary = {
            "car": car,
            "count": len(passengers),
            "existing_count": sum(bool(child.bib_number) for child in passengers),
            "new_count": sum(not child.bib_number for child in passengers),
            "outside_range_count": sum(
                bool(child.bib_number) and child.bib_number not in number_range for child in passengers
            )
            if car.bib_prefix is not None
            else 0,
        }
        summaries.append(summary)
        if car.bib_prefix is None:
            continue
        if len(passengers) > 99:
            errors.append({"message": _("Le car %(car)s dépasse la limite de 99 enfants.") % {"car": car}, "car": car})
            continue
        passengers.sort(key=lambda child: (_alphabetical(child.last_name), _alphabetical(child.first_name), child.pk))
        try:
            changed.extend(assign(car, passengers, reserved))
        except ValidationError as error:
            errors.extend({"message": message, "car": car} for message in error.messages)
    return {
        "errors": errors,
        "changed": changed,
        "cars": summaries,
        "children_count": len(children),
        "existing_count": existing_count,
        "new_count": len(children) - existing_count,
        "can_generate": bool(children) and not errors,
    }


@transaction.atomic
def generate_bibs(*, overwrite=False):
    # Rebuild under locks: a preview must never authorize stale assignments or numbers.
    plan = prepare_bibs(overwrite=overwrite, lock=True)
    if plan["errors"]:
        raise ValidationError([error["message"] for error in plan["errors"]])
    changed = plan["changed"]
    for child in changed:
        child.modified = now()
    if changed:
        Child.objects.bulk_update(changed, ["bib_number", "modified"])
    return len(changed)
