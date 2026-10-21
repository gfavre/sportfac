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


def _reserve_existing_bibs(children, reserved):
    for child in children:
        if not child.bib_number:
            continue
        if child.bib_number in reserved:
            raise ValidationError(
                _(
                    "Le dossard %(number)s est déjà attribué à plusieurs enfants. "
                    "Corrigez ce doublon avant de continuer."
                )
                % {"number": child.bib_number}
            )
        reserved.add(child.bib_number)


def _replace_bibs(car, passengers, reserved):
    for rank, child in enumerate(passengers, 1):
        number = f"{car.bib_prefix}{rank:02d}"
        if number in reserved:
            raise ValidationError(_("Un dossard calculé est déjà attribué à un enfant hors de cette génération."))
        child.bib_number = number
        reserved.add(number)
    return passengers


@transaction.atomic
def generate_bibs(*, overwrite=False):
    # Serialize generation calls, including calls made before any bib exists.
    transports = {car.pk: car for car in Transport.objects.select_for_update().order_by("pk")}
    assignments = defaultdict(set)
    for registration in Registration.objects.select_for_update().order_by("pk"):
        assignments[registration.child_id].add(registration.transport_id)
    children = list(Child.objects.select_for_update().filter(pk__in=assignments).order_by("pk"))
    if not children:
        raise ValidationError(_("Aucun enfant avec une inscription active à numéroter."))
    groups = defaultdict(list)
    for child in children:
        cars = assignments[child.pk]
        if None in cars or len(cars) != 1:
            raise ValidationError(
                _("%(child)s doit être affecté à un seul car sur toutes ses inscriptions actives.") % {"child": child}
            )
        car = transports[next(iter(cars))]
        if car.bib_prefix is None:
            raise ValidationError(_("Le car %(car)s n'a pas de préfixe de dossard.") % {"car": car})
        groups[car.pk].append(child)
    # Keep distributed numbers reserved, including those of canceled/unregistered children.
    reserved = set(
        Child.objects.exclude(pk__in=assignments).exclude(bib_number="").values_list("bib_number", flat=True)
    )
    if not overwrite:
        _reserve_existing_bibs(children, reserved)
    changed = []
    assign = _replace_bibs if overwrite else _assign_missing_bibs
    for car_id, passengers in groups.items():
        if len(passengers) > 99:
            raise ValidationError(_("Le car %(car)s dépasse la limite de 99 enfants.") % {"car": transports[car_id]})
        passengers.sort(key=lambda child: (_alphabetical(child.last_name), _alphabetical(child.first_name), child.pk))
        changed.extend(assign(transports[car_id], passengers, reserved))
    for child in changed:
        child.modified = now()
    if changed:
        Child.objects.bulk_update(changed, ["bib_number", "modified"])
    return len(changed)
