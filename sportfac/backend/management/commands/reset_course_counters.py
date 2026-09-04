from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from activities.models import Course
from backend.models import YearTenant
from backend.tenant_utils import using_tenant


class Command(BaseCommand):
    help = _("Reset denormalized course counters for a tenant (run after copying to a new period).")

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
        # The [y/N] hint and the "y" comparison below are deliberately left untranslated:
        # gettext() renders the confirmation prompt in the active language (fr-CH by
        # default here), which used to translate the hint to "[O/N]" while this check kept
        # comparing against the English "y" - so answering "o" (the French "oui", exactly
        # what the on-screen hint told the user to type) always read as a no and silently
        # aborted. Re-prompts instead of aborting on an unrecognized answer, matching
        # _prompt_yes_no in the sibling copy_tenant_data command.
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

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(_("Will reset on %(schema)s:") % {"schema": tenant.schema_name}))
        self.stdout.write("  nb_participants          → 0")
        self.stdout.write("  has_waiting_list         → False")
        self.stdout.write("  places_available_reminder_sent_on → None")
        self.stdout.write("  announced_js             → False")
        self.stdout.write("  allow_new_participants   → True")
        self.stdout.write("  uptodate                 → False")
        self.stdout.write("")

        if not self._prompt_yes_no(_("Proceed?")):
            self.stdout.write(self.style.WARNING(_("Aborted.")))
            return

        with using_tenant(tenant):
            updated = Course.objects.all().update(
                uptodate=False,
                nb_participants=0,
                has_waiting_list=False,
                places_available_reminder_sent_on=None,
                announced_js=False,
                allow_new_participants=True,
            )

        self.stdout.write(
            self.style.SUCCESS(
                _("%(count)d course(s) reset in %(schema)s.")
                % {
                    "count": updated,
                    "schema": tenant.schema_name,
                }
            )
        )
