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
    if not overwrite and any(child.bib_number for child in children):
        raise ValidationError(_("Des dossards existent déjà. Confirmez leur remplacement pour les recalculer."))
    for car_id, passengers in groups.items():
        if len(passengers) > 99:
            raise ValidationError(_("Le car %(car)s dépasse la limite de 99 enfants.") % {"car": transports[car_id]})
        passengers.sort(key=lambda child: (_alphabetical(child.last_name), _alphabetical(child.first_name), child.pk))
        for rank, child in enumerate(passengers, 1):
            child.bib_number = f"{transports[car_id].bib_prefix}{rank:02d}"
            child.modified = now()
    # Preserve bibs belonging to children outside the generated population.
    if Child.objects.exclude(pk__in=assignments).filter(bib_number__in=[c.bib_number for c in children]).exists():
        raise ValidationError(_("Un dossard calculé est déjà attribué à un enfant hors de cette génération."))
    Child.objects.bulk_update(children, ["bib_number", "modified"])
    return len(children)
