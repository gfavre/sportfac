from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count
from django.db.models.functions import Lower

from ...models import FamilyUser


class Command(BaseCommand):
    help = (
        "Lowercase every FamilyUser.email on a given database, so login (case-insensitive "
        "since profiles.0026) actually finds an account regardless of how the user types "
        "their email. Accounts that would collide with another once lowercased are left "
        "untouched and reported instead - merging them is a manual, human call.\n\n"
        "profiles.0026_lowercase_familyuser_email already does this for every tenant schema "
        "on the default database, but Montreux's shared identity database (MASTER_DB, e.g. "
        "'master_users') is explicitly excluded from all migrations (see "
        "MasterRouter.allow_migrate) and only ever reachable via --database. This command "
        "also lets you re-run the sweep later, e.g. after manually resolving a reported "
        "collision."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Database alias to fix (e.g. 'master_users' for Montreux's shared identity "
            "database). Defaults to the current tenant's database.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without saving anything.",
        )

    def handle(self, *args, **options):
        db = options["database"]
        dry_run = options["dry_run"]
        users = FamilyUser.objects.using(db)

        colliding_emails = set(
            # order_by(): FamilyUser.Meta.ordering ("last_name", "first_name") would
            # otherwise leak into GROUP BY here (a well-known Django gotcha), splitting a
            # genuine email collision into separate groups - and hiding it - whenever the
            # two accounts don't share the exact same name.
            users.order_by()
            .annotate(lower_email=Lower("email"))
            .values("lower_email")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
            .values_list("lower_email", flat=True)
        )

        fixed = 0
        skipped = []
        for user in users.all():
            lowered = user.email.strip().lower()
            if lowered == user.email:
                continue
            if lowered in colliding_emails:
                skipped.append((user.pk, user.email))
                continue
            fixed += 1
            if not dry_run:
                user.email = lowered
                user.save(using=db, update_fields=["email"])

        verb = "Would fix" if dry_run else "Fixed"
        self.stdout.write(self.style.SUCCESS(f"{verb} {fixed} email(s) on database {db!r}."))
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {len(skipped)} account(s) needing manual review "
                    "(would collide with another account once lowercased):"
                )
            )
            for pk, email in skipped:
                self.stdout.write(f"  - {pk}: {email!r}")
