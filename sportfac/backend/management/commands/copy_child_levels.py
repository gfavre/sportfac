from collections import Counter

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django_tenants.utils import get_public_schema_name
from django_tenants.utils import schema_context

from activities.models import Activity
from backend.models import YearTenant
from registrations.models import Child
from registrations.models import ChildActivityLevel


def child_key(child):
    return child.id_lagapeo


class Command(BaseCommand):
    help = "Copie les after_level d'une période dans les before_level d'une période ultérieure."

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Nom du schéma source")
        parser.add_argument("--destination", help="Nom du schéma destination")
        parser.add_argument("--dry-run", action="store_true", help="Afficher le bilan sans écrire")
        parser.add_argument("--overwrite", action="store_true", help="Remplacer aussi les before_level non vides")

    def select_period(self, periods, schema, title):
        if schema:
            for period in periods:
                if period.schema_name == schema:
                    return period
            raise CommandError(f"Période inconnue ou non prête: {schema}")
        if not periods:
            raise CommandError("Aucune période admissible.")
        self.stdout.write(title)
        for index, period in enumerate(periods, 1):
            self.stdout.write(f"{index}. {period} [{period.schema_name}]")
        while True:
            try:
                answer = input("Numéro (q pour annuler): ").strip()
            except (EOFError, KeyboardInterrupt) as exc:
                raise CommandError("Sélection annulée; fournir --source et --destination sans terminal.") from exc
            if answer.lower() == "q":
                raise CommandError("Annulé.")
            if answer.isdigit() and 1 <= int(answer) <= len(periods):
                return periods[int(answer) - 1]
            self.stdout.write("Choix invalide.")

    def handle(self, *args, **options):
        with schema_context(get_public_schema_name()):
            periods = list(
                YearTenant.objects.filter(status=YearTenant.STATUS.ready)
                .exclude(schema_name=get_public_schema_name())
                .order_by("start_date", "schema_name")
            )
        source = self.select_period(periods, options["source"], "Période source:")
        later = [period for period in periods if period.start_date > source.start_date]
        destination = self.select_period(later, options["destination"], "Période destination (ultérieure):")
        self.stdout.write(f"{source.schema_name} → {destination.schema_name}")
        counts = self.copy_levels(
            source.schema_name, destination.schema_name, options["dry_run"], options["overwrite"]
        )
        prefix = "Simulation" if options["dry_run"] else "Copie terminée"
        self.stdout.write(f"{prefix}: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))

    def copy_levels(self, source, destination, dry_run=False, overwrite=False):
        counts = Counter(created=0, updated=0, preserved=0, unmatched=0, ambiguous=0)
        with schema_context(source):
            children = list(Child.objects.all())
            keys = Counter(child_key(child) for child in children)
            levels = list(ChildActivityLevel.objects.exclude(after_level="").select_related("child", "activity"))
            # Materialize all source values before changing the connection's schema.
            rows = [(child_key(level.child), level.activity.name, level.after_level) for level in levels]
        with schema_context(destination), transaction.atomic():
            destination_children = {}
            for child in Child.objects.all():
                destination_children.setdefault(child_key(child), []).append(child.pk)
            activities = dict(Activity.objects.values_list("name", "pk"))
            for key, name, value in rows:
                matches = destination_children.get(key, [])
                if key is None or not matches or name not in activities:
                    counts["unmatched"] += 1
                    continue
                if keys[key] != 1 or len(matches) != 1:
                    counts["ambiguous"] += 1
                    continue
                level = (
                    ChildActivityLevel.objects.select_for_update()
                    .filter(child_id=matches[0], activity_id=activities[name])
                    .first()
                )
                if level and (level.before_level == value or (level.before_level and not overwrite)):
                    counts["preserved"] += 1
                    continue
                counts["updated" if level else "created"] += 1
                if dry_run:
                    continue
                if level:
                    level.before_level = value
                    level.save(update_fields=["before_level", "modified"])
                else:
                    ChildActivityLevel.objects.create(
                        child_id=matches[0], activity_id=activities[name], before_level=value
                    )
        return counts
