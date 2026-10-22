from registrations.models import Child
from registrations.models import Registration


def children_eligible_for_rental(user):
    """A course selected in the wizard counts; a canceled registration does not."""
    return Child.objects.filter(
        family=user,
        registrations__status__in=(
            Registration.STATUS.waiting,
            Registration.STATUS.valid,
            Registration.STATUS.confirmed,
        ),
    ).distinct()
