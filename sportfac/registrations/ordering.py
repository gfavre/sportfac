from django.conf import settings


def order_participants_by_bib(registrations):
    """Sort by numeric bib, then surname and first name; missing bibs come last."""
    registrations = list(registrations)

    def sort_key(registration):
        child = registration.child
        number = float("inf")
        if settings.KEPCHUP_BIB_NUMBERS:
            try:
                number = int(child.bib_number)
            except (TypeError, ValueError):
                pass
        return number, child.last_name.casefold(), child.first_name.casefold(), registration.pk

    return sorted(registrations, key=sort_key)
