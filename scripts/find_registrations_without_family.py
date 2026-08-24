"""Find non-canceled registrations whose child has no family (family_id NULL), across
every tenant. Triggered by a Sentry alert (SPORTFAC-Y7, LTDP, 2026-08-24): Registration
166 for child 645 "Alya Koksoy" hit this in Registration.is_local_pricing
(registrations/models.py), which logs an error and falls back to non-local pricing
whenever it happens - Child.family is nullable, so this doesn't crash anything, but it
does mean that registration is silently billed at non-local pricing regardless of the
family's real address, and something upstream let a family-less child collect a real
registration + bill in the first place (Child.family is on_delete=CASCADE, so a deleted
family account would have taken the child down with it - this isn't that).

Read-only - lists candidates, changes nothing. Output is Markdown.

Paste into `python manage.py shell`.
"""
from django_tenants.utils import tenant_context

from backend.models import YearTenant
from registrations.models import Registration


for tenant in YearTenant.objects.filter(status=YearTenant.STATUS.ready):
    with tenant_context(tenant):
        orphaned = (
            Registration.objects.exclude(status=Registration.STATUS.canceled)
            .filter(child__family__isnull=True)
            .select_related("child", "course", "course__activity", "bill")
        )
        if not orphaned.exists():
            continue

        print(f"## {tenant} ({tenant.schema_name}) - {orphaned.count()} inscription(s) sans famille\n")
        print("| Registration | Enfant | Cours | Bill |")
        print("|---|---|---|---|")
        for reg in orphaned:
            child = f"{reg.child.first_name} {reg.child.last_name} (id={reg.child.pk})"
            course = f"{reg.course.activity.name} - {reg.course.number}" if reg.course else ""
            bill = f"#{reg.bill.pk} ({reg.bill.status})" if reg.bill else "(pas de facture)"
            print(f"| #{reg.pk} ({reg.status}) | {child} | {course} | {bill} |")
        print()
