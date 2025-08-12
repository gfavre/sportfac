# tenants/management/commands/copy_tenant_data.py
from __future__ import annotations

import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _

from backend.models import YearTenant
from backend.tenant_utils import copy_activities  # adjust import path if needed
from backend.tenant_utils import copy_children
from backend.tenant_utils import copy_payroll_functions


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = _("Interactively copy data (children, activities, payroll) from one tenant to another.")

    def _prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """
        Prompt a yes/no question.

        Args:
            question: The question to display.
            default: Default answer if user presses Enter.

        Returns:
            True for yes, False for no.
        """
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            answer = input(f"{question} {suffix} ").strip().lower()
            if not answer:
                return default
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            self.stdout.write(self.style.WARNING(_("Please answer 'y' or 'n'.")))

    def _select_tenant(self, title: str) -> YearTenant | None:
        """
        Present a numbered list of tenants and let the user pick one.

        Args:
            title: List title displayed before options.

        Returns:
            The selected YearTenant or None if aborted.
        """
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(title))
        tenants = list(YearTenant.objects.order_by("-start_date", "-end_date", "schema_name"))
        if not tenants:
            self.stdout.write(self.style.ERROR(_("No tenants found.")))
            return None

        for idx, t in enumerate(tenants, start=1):
            label = f"{idx:>2}. id={t.id} schema={t.schema_name} {t.start_date} → {t.end_date} status={t.status}"
            self.stdout.write(label)

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

    def handle(self, *args, **options) -> None:
        """
        Run the interactive copy wizard.
        """
        dest = self._select_tenant(_("Select destination period (tenant):"))
        if not dest:
            self.stdout.write(self.style.WARNING(_("Aborted.")))
            return

        do_children = self._prompt_yes_no(_("Copy children?"), default=True)
        src_children: YearTenant | None = None
        if do_children:
            src_children = self._select_tenant(_("Select source for children:"))
            if not src_children:
                self.stdout.write(self.style.WARNING(_("Children copy skipped.")))
                do_children = False

        do_activities = self._prompt_yes_no(_("Copy activities?"), default=True)
        src_activities: YearTenant | None = None
        if do_activities:
            src_activities = self._select_tenant(_("Select source for activities:"))
            if not src_activities:
                self.stdout.write(self.style.WARNING(_("Activities copy skipped.")))
                do_activities = False

        do_payroll = False
        if getattr(settings, "KEPCHUP_ENABLE_PAYROLLS", False) and do_activities:
            do_payroll = self._prompt_yes_no(
                _("Copy payroll functions (from the same activities source)?"),
                default=True,
            )

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO(_("Summary")))
        self.stdout.write(f"- Destination: {dest.schema_name} ({dest.start_date} → {dest.end_date})")
        self.stdout.write(
            f"- Children:    {bool(do_children)}{' from ' + src_children.schema_name if src_children else ''}"
        )
        self.stdout.write(
            f"- Activities:  {bool(do_activities)}"
            f"{' from ' + src_activities.schema_name if src_activities else ''}"
        )
        if getattr(settings, "KEPCHUP_ENABLE_PAYROLLS", False):
            self.stdout.write(f"- Payroll:     {bool(do_payroll)}")
        proceed = self._prompt_yes_no(_("Proceed?"), default=True)
        if not proceed:
            self.stdout.write(self.style.WARNING(_("Aborted.")))
            return

        if do_children and src_children:
            copy_children(src_children, dest, logger=logger)

        if do_activities and src_activities:
            copy_activities(src_activities, dest, logger=logger)
            if do_payroll:
                copy_payroll_functions(src_activities, dest, logger=logger)

        self.stdout.write(self.style.SUCCESS(_("Done.")))
