from pathlib import Path

from dbtemplates.models import Template
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from backend.models import YearTenant
from mailer.models import GenericEmail
from mailer.practical_reminder import BODY_TEMPLATE
from mailer.practical_reminder import SUBJECT_TEMPLATE


class Command(BaseCommand):
    help = "Install the Montreux winter practical reminder mail type for an explicit period."

    def add_arguments(self, parser):
        parser.add_argument("--schema", required=True, help="Target school-year schema")
        parser.add_argument("--replace", action="store_true", help="Replace existing subject/body edits")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not settings.KEPCHUP_PRACTICAL_REMINDER:
            raise CommandError("Le rappel pratique n’est pas activé dans ce déploiement.")
        schema = options["schema"]
        if schema == "public" or not YearTenant.objects.filter(schema_name=schema).exists():
            raise CommandError("Choisissez le schéma d’une période existante, hors public.")
        body = (Path(__file__).parents[2] / "templates/mailer/defaults/montreux_practical_reminder.html").read_text()
        with schema_context(schema), transaction.atomic():
            templates = []
            for name, content in (
                (SUBJECT_TEMPLATE, "Rappel d’informations SSF hiver {{ year }}"),
                (BODY_TEMPLATE, body),
            ):
                template, created = Template.objects.get_or_create(name=name, defaults={"content": content})
                if not created and options["replace"]:
                    template.content = content
                    template.save()
                templates.append(template)
            GenericEmail.objects.get_or_create(
                body_template=templates[1],
                defaults={
                    "subject": "Rappel des informations pratiques — Montreux hiver",
                    "subject_template": templates[0],
                    "help_text": "Données disponibles : child, course, registration, year, logo_url. "
                    "Les horaires et consignes sont ceux du modèle Montreux : vérifiez-les avant l’envoi.",
                },
            )
            if options["dry_run"]:
                transaction.set_rollback(True)
        result = (
            "simulation terminée" if options["dry_run"] else "mail type installé (éditions conservées sauf --replace)"
        )
        self.stdout.write(self.style.SUCCESS(f"{schema} : {result}."))
