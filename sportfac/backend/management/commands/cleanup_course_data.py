from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.core.management.base import CommandParser
from django.utils.translation import gettext as _

from activities.models import Course
from backend.models import YearTenant
from backend.tenant_utils import using_tenant


class Command(BaseCommand):
    help = _(
        "Recompute denormalized course counters (nb_participants, has_waiting_list) for a "
        "tenant from actual registration/waiting-list data, by re-running Course.save()'s "
        "own self-healing logic. Unlike reset_course_counters, this never zeroes anything "
        "out blindly and, by default, leaves allow_new_participants untouched - it's a "
        "manual staff choice ('more restrictive than the course being full'), not derived "
        "data. Pass --override-openness to also recompute it (True if not full, False if "
        "full), which does overwrite that choice."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--override-openness",
            action="store_true",
            help=_(
                "Also recompute allow_new_participants: True if the course isn't full, "
                "False if it is. Overwrites any manual staff decision to close a course "
                "early or keep a full one open."
            ),
        )

    def _select_tenant(self) -> YearTenant | None:
        tenants = list(YearTenant.objects.order_by("-start_date", "-end_date", "schema_name"))
        if not tenants:
            self.stdout.write(self.style.ERROR(_("No YearTenant found.")))
            return None

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(_("Select tenant:")))
        for idx, t in enumerate(tenants, start=1):
            self.stdout.write(
                f"{idx:>2}. schema={t.schema_name} {t.start_date} → {t.end_date} status={t.status} (id={t.id})"
            )

        self.stdout.write(_("Enter number or 'q' to cancel."))
        while True:
            raw = input("> ").strip().lower()
            if raw in {"q", "quit", "exit"}:
                return None
            if raw.isdigit():
                i = int(raw)
                if 1 <= i <= len(tenants):
                    return tenants[i - 1]
            self.stdout.write(self.style.WARNING(_("Invalid choice, try again.")))

    def _prompt_yes_no(self, question: str) -> bool:
        # [y/N] deliberately left untranslated - see reset_course_counters._prompt_yes_no
        # for why (gettext() translated it to "[O/N]" on this project's fr-CH default
        # locale while the check still compared against the English "y", so typing the
        # French "oui" silently read as a no).
        while True:
            answer = input(f"{question} [y/N] ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"", "n", "no"}:
                return False
            self.stdout.write(self.style.WARNING(_("Please answer 'y' or 'n'.")))

    def handle(self, *args: Any, **options: Any) -> None:
        tenant = self._select_tenant()
        if not tenant:
            self.stdout.write(self.style.WARNING(_("Aborted.")))
            return

        override_openness = options["override_openness"]

        with using_tenant(tenant):
            nb_courses = Course.objects.count()

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(_("Will recompute on %(schema)s:") % {"schema": tenant.schema_name}))
        self.stdout.write("  nb_participants          → recounted from actual registrations")
        self.stdout.write("  has_waiting_list         → recounted from actual waiting slots")
        if override_openness:
            self.stdout.write(
                "  allow_new_participants   → True if not full, "
                "False if full "
                "(OVERWRITES any manual staff choice)"
            )
        else:
            self.stdout.write("  allow_new_participants   → left untouched (pass --override-openness to include it)")
        self.stdout.write(_("  %(count)d course(s) in this tenant") % {"count": nb_courses})
        self.stdout.write("")

        if not self._prompt_yes_no(_("Proceed?")):
            self.stdout.write(self.style.WARNING(_("Aborted.")))
            return

        openness_flipped = 0
        with using_tenant(tenant):
            for course in Course.objects.all():
                # Course.save() already self-heals nb_participants and has_waiting_list on
                # every save (activities/models/courses.py) - reusing it here rather than
                # re-deriving the same counts keeps this command in sync with that logic
                # instead of drifting from it.
                course.save()
                if override_openness:
                    should_be_open = not course.full
                    if course.allow_new_participants != should_be_open:
                        course.allow_new_participants = should_be_open
                        course.save(update_fields=["allow_new_participants"])
                        openness_flipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                _("%(count)d course(s) recomputed in %(schema)s.")
                % {"count": nb_courses, "schema": tenant.schema_name}
            )
        )
        if override_openness:
            self.stdout.write(
                self.style.SUCCESS(
                    _("%(count)d course(s) had allow_new_participants flipped.") % {"count": openness_flipped}
                )
            )
