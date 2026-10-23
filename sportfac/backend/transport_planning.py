from collections import defaultdict

from registrations.models import Registration


def transport_occupancy(transports):
    """Count unique children per date, matching car sheets rather than total registrations."""
    by_date = {car.pk: defaultdict(set) for car in transports}
    undated = {car.pk: set() for car in transports}
    dates_by_course = {}
    for registration in (
        Registration.objects.filter(transport_id__in=by_date)
        .select_related("course")
        .prefetch_related("course__sessions")
    ):
        if registration.course_id not in dates_by_course:
            dates_by_course[registration.course_id] = registration.course.all_dates
        dates = dates_by_course[registration.course_id]
        if not dates:
            undated[registration.transport_id].add(registration.child_id)
        for day in dates:
            by_date[registration.transport_id][day].add(registration.child_id)
    results = {}
    for car in transports:
        dates = by_date[car.pk]
        peak_date = max(dates, key=lambda day: (len(dates[day]), day)) if dates else None
        peak = len(dates[peak_date]) if peak_date else 0
        results[car.pk] = {
            "peak": peak,
            "peak_date": peak_date,
            "undated_count": len(undated[car.pk]),
            "remaining": max(car.capacity - peak, 0) if car.capacity is not None else None,
            "over_capacity": car.capacity is not None and peak > car.capacity,
        }
    return results
