from pathlib import Path

from dbtemplates.models import Template
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django_tenants.utils import get_public_schema_name
from django_tenants.utils import schema_context

from backend.models import YearTenant
from mailer.models import GenericEmail


SUBJECT_TEMPLATE = "registrations/rental_bill_mail_subject.txt"
BODY_TEMPLATE = "registrations/rental_bill_mail.txt"


class Command(BaseCommand):
    help = "Install the editable rental invoice email without overwriting existing content."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only; do not write templates or caches")

    def handle(self, *args, **options):
        if not settings.KEPCHUP_USE_APPOINTMENTS:
            raise CommandError("La location de matériel n’est pas activée dans ce déploiement.")
        root = Path(settings.SITE_ROOT) / "registrations" / "templates"
        defaults = {name: (root / name).read_text(encoding="utf-8") for name in (SUBJECT_TEMPLATE, BODY_TEMPLATE)}
        with schema_context(get_public_schema_name()):
            if options["dry_run"]:
                for name in defaults:
                    action = "conservé" if Template.objects.filter(name=name).exists() else "à créer"
                    self.stdout.write(f"{name}: {action}")
                self.stdout.write("Simulation: aucune écriture. Le mail type sera créé s’il manque.")
                return
            with transaction.atomic():
                templates = {}
                for name, content in defaults.items():
                    try:
                        templates[name], _ = Template.objects.get_or_create(name=name, defaults={"content": content})
                    except Template.MultipleObjectsReturned as exc:
                        raise CommandError(f"Plusieurs modèles portent le nom {name}; corrigez les doublons.") from exc
                mail_type, created = GenericEmail.objects.get_or_create(
                    body_template=templates[BODY_TEMPLATE],
                    defaults={
                        "subject": "Facture de location de matériel",
                        "is_html": False,
                        "subject_template": templates[SUBJECT_TEMPLATE],
                        "help_text": (
                            "<p>Variables disponibles: <code>bill</code> (facture), <code>rentals</code> "
                            "(locations de cette facture), <code>user</code>, <code>site_url</code>, "
                            "<code>site_name</code>, <code>signature</code>.</p>"
                            "<p>Chaque location contient <code>child</code>, <code>amount</code>, "
                            "<code>pickup_appointment</code> et <code>return_appointment</code>. "
                            "Les rendez-vous peuvent être absents. Conservez le lien "
                            "<code>{{ site_url }}{{ bill.get_absolute_url }}</code>: les parents doivent "
                            "se connecter pour consulter la facture et payer.</p>"
                        ),
                    },
                )
            action = "installé" if created else "déjà installé"
            self.stdout.write(self.style.SUCCESS(f"Mail type partagé {action}; textes existants conservés."))
            self.stdout.write(f"Édition dans le backend: {mail_type.get_absolute_url()}")
            # Template tables are shared, but dbtemplates cache keys can be schema-specific.
            from dbtemplates.utils.cache import remove_cached_template
            from dbtemplates.utils.cache import remove_notfound_key

            schemas = set(YearTenant.objects.values_list("schema_name", flat=True)) | {get_public_schema_name()}
            for schema in schemas:
                with schema_context(schema):
                    for template in templates.values():
                        remove_cached_template(template)
                        remove_notfound_key(template)
