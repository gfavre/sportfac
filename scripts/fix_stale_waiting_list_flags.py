"""Find (and fix) courses whose denormalized `has_waiting_list` flag has drifted from
reality - it's only ever updated by a signal on WaitingSlot post_save/post_delete
(activities/signals.py), with nothing to self-correct it if it ever goes stale once
(race condition, a state predating that signal, a direct DB edit...). Reported for
Oron's BOXE.2: has_waiting_list=True with 0 participants and 0 actual waiting slots,
silently blocking new registrations via Course.accepts_registrations.

`Course.save()` now self-heals this on every save (see activities/models/courses.py),
so this only matters for courses stuck *before* that fix is deployed - safe to run
again after deploying too, it'll just find nothing.

This actually fixes what it finds (setting a denormalized flag to match the real
`waiting_slots.exists()` state is a safe, idempotent correction, not a deletion).
Output is Markdown.

Paste into `python manage.py shell`.
"""
from django_tenants.utils import tenant_context

from activities.models import Course
from backend.models import YearTenant


for tenant in YearTenant.objects.filter(status=YearTenant.STATUS.ready):
    with tenant_context(tenant):
        stuck = []
        for course in Course.objects.all():
            real_state = course.waiting_slots.exists()
            if course.has_waiting_list != real_state:
                stuck.append((course, real_state))

        if not stuck:
            continue

        print(f"## {tenant} ({tenant.schema_name}) - {len(stuck)} cours désynchronisé(s)\n")
        print("| Cours | has_waiting_list (avant) | Inscrits | Liste d'attente réelle |")
        print("|---|---|---|---|")
        for course, real_state in stuck:
            print(f"| {course} | {course.has_waiting_list} | {course.nb_participants} | {real_state} |")
            course.has_waiting_list = real_state
            course.save(update_fields=["has_waiting_list"])
        print()
