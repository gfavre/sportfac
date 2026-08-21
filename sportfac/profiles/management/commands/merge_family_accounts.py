from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import Lower

from absences.models import Session
from activities.models import Activity
from activities.models import CoursesInstructors
from activities.models import PaySlip
from appointments.models import Appointment
from payroll.models import Payroll
from registrations.models import Bill
from registrations.models import Child
from registrations.models import Registration
from registrations.models import RegistrationsProfile
from registrations.models import RegistrationValidation

from ...models import FamilyUser


# Plain (model, field_name) FKs pointing at FamilyUser that a straight bulk .update() can
# repoint safely - i.e. nothing else constrains them to be unique per account. Excludes
# CoursesInstructors.instructor (unique_together with course - see _merge_instructor_rows),
# RegistrationsProfile.user (OneToOneField, can't coexist - see _merge_profile), and
# Activity.managers (a plain M2M, needs add()/remove() rather than update()). PermissionsMixin's
# groups/user_permissions are deliberately left out too: nothing in this app actually reads
# them (it uses its own is_admin/is_manager/is_restricted_manager flags instead).
REASSIGNABLE_FK_FIELDS = [
    (Session, "instructor"),
    (PaySlip, "instructor"),
    (Registration, "cancelation_person"),
    (Bill, "family"),
    (RegistrationValidation, "user"),
    (Child, "family"),
    (Payroll, "exported_by"),
    (Appointment, "family"),
]

# Boolean role flags: never auto-elevated onto the winner (a merge shouldn't silently grant
# permissions), just reported so a human can decide whether to grant them by hand afterwards.
ROLE_FLAGS = ["is_admin", "is_manager", "is_restricted_manager", "is_staff", "is_superuser", "is_teacher", "is_mep"]


class Command(BaseCommand):
    help = (
        "Interactively merge case-variant duplicate FamilyUser accounts (see "
        "lowercase_family_emails) on the current tenant's database: for each pair, pick "
        "which account to keep (defaults to whichever logged in most recently), reassign "
        "every relation pointing at the other one onto it, then soft_delete() the other.\n\n"
        "Scoped to one tenant's business data (children, courses, bills...) - run it via "
        "'tenant_command' / 'all_tenants_command' to pick a schema. Montreux's shared "
        "identity database (master_users) has nothing to merge beyond the email itself, "
        "already handled by lowercase_family_emails --database=master_users."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to operate on. Defaults to the current tenant's database.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what each merge would do without prompting or saving anything.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        dry_run = options["dry_run"]

        lower_emails = list(
            FamilyUser.objects.using(db)
            .order_by()
            .annotate(lower_email=Lower("email"))
            .values("lower_email")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .values_list("lower_email", flat=True)
        )
        if not lower_emails:
            self.stdout.write(self.style.SUCCESS("No case-variant duplicate accounts found."))
            return

        for lower_email in lower_emails:
            accounts = list(
                FamilyUser.objects.using(db)
                .annotate(lower_email=Lower("email"))
                .filter(lower_email=lower_email)
                .order_by("-date_joined")
            )
            self._handle_group(accounts, db, dry_run)

    def _handle_group(self, accounts, db, dry_run):
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(f"Duplicate group: {accounts[0].email.lower()}"))
        for idx, account in enumerate(accounts, start=1):
            self.stdout.write(
                f"  {idx}. {account.email!r} - {account.first_name} {account.last_name} "
                f"(pk={account.pk}, last_login={account.last_login}, date_joined={account.date_joined}, "
                f"active={account.is_active})"
            )

        suggested = max(accounts, key=lambda a: a.last_login or a.date_joined)
        suggested_idx = accounts.index(suggested) + 1

        if dry_run:
            self.stdout.write(f"  Would suggest keeping #{suggested_idx} ({suggested.email!r}).")
            winner = suggested
            losers = [a for a in accounts if a.pk != winner.pk]
        else:
            choice = input(f"Keep which account? [{suggested_idx}] (number, or 's' to skip this group) ").strip()
            if choice.lower() == "s":
                self.stdout.write(self.style.WARNING("Skipped."))
                return
            if not choice:
                choice = str(suggested_idx)
            if not choice.isdigit() or not (1 <= int(choice) <= len(accounts)):
                self.stdout.write(self.style.ERROR("Invalid choice, skipping this group."))
                return
            winner = accounts[int(choice) - 1]
            losers = [a for a in accounts if a.pk != winner.pk]

        for loser in losers:
            self._merge_one(winner, loser, db, dry_run=True)

        if dry_run:
            return

        confirm = input(f"Merge {len(losers)} account(s) into {winner.email!r} and soft-delete them? (y/N) ")
        if confirm.strip().lower() != "y":
            self.stdout.write(self.style.WARNING("Aborted."))
            return

        for loser in losers:
            with transaction.atomic(using=db):
                self._merge_one(winner, loser, db, dry_run=False)
        self.stdout.write(self.style.SUCCESS(f"Merged into {winner.email!r}."))

    def _merge_one(self, winner, loser, db, dry_run):
        report = []

        for model, field in REASSIGNABLE_FK_FIELDS:
            qs = model.objects.using(db).filter(**{field: loser})
            count = qs.count()
            if not count:
                continue
            report.append(f"{model.__name__}.{field}: {count}")
            if not dry_run:
                qs.update(**{field: winner})

        report += self._merge_instructor_rows(winner, loser, db, dry_run)
        report += self._merge_managed_activities(winner, loser, db, dry_run)
        if RegistrationsProfile.objects.using(db).filter(user=loser).exists():
            report.append("RegistrationsProfile: dropped (cache, recomputed for winner)")

        elevated_flags = [flag for flag in ROLE_FLAGS if getattr(loser, flag) and not getattr(winner, flag)]
        if elevated_flags:
            report.append(
                f"NOT copied (review manually): {loser.email!r} has {', '.join(elevated_flags)} "
                f"that {winner.email!r} doesn't"
            )

        prefix = "Would merge" if dry_run else "Merging"
        self.stdout.write(f"  {prefix} {loser.email!r} (pk={loser.pk}) into {winner.email!r}:")
        for line in report or ["  (nothing to reassign)"]:
            self.stdout.write(f"    - {line}")

        if not dry_run:
            # soft_delete() itself calls self.save() with its own create_profile=True
            # default, which would silently recreate a RegistrationsProfile for the loser
            # via get_or_create() - so drop it (again) after soft_delete() runs, as the
            # true last step, not before.
            loser.soft_delete()
            RegistrationsProfile.objects.using(db).filter(user=loser).delete()
            winner_profile, _ = RegistrationsProfile.objects.using(db).get_or_create(user=winner)
            winner_profile.save(using=db)

        return report

    def _merge_instructor_rows(self, winner, loser, db, dry_run):
        # CoursesInstructors.instructor is unique_together with course (a person can't be
        # listed twice as instructor on the same course) - if the winner is already the
        # instructor there, the loser's row is a pure duplicate to drop, not move.
        moved = dropped = 0
        for ci in CoursesInstructors.objects.using(db).filter(instructor=loser):
            if CoursesInstructors.objects.using(db).filter(course_id=ci.course_id, instructor=winner).exists():
                dropped += 1
                if not dry_run:
                    ci.delete()
            else:
                moved += 1
                if not dry_run:
                    ci.instructor = winner
                    ci.save(using=db, update_fields=["instructor"])
        if not (moved or dropped):
            return []
        return [f"CoursesInstructors: {moved} moved, {dropped} dropped (winner already instructor there)"]

    def _merge_managed_activities(self, winner, loser, db, dry_run):
        activities = list(Activity.objects.using(db).filter(managers=loser))
        if not activities:
            return []
        if not dry_run:
            for activity in activities:
                activity.managers.add(winner)
                activity.managers.remove(loser)
        return [f"Activity.managers: {len(activities)}"]
