from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django_tenants.utils import get_public_schema_name
from django_tenants.utils import schema_context
from django_tenants.utils import tenant_context

from activities.tests.factories import ActivityFactory
from backend.models import YearTenant
from registrations.models import ChildActivityLevel
from registrations.tests.factories import ChildFactory
from sportfac.utils import TenantTestCase


class CopyChildLevelsTests(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.destination = YearTenant(
            schema_name="test_level_destination",
            start_date=date(2016, 1, 1),
            end_date=date(2016, 12, 31),
            status="ready",
        )
        with schema_context(get_public_schema_name()):
            cls.destination.save()
            cls.destination.create_schema(verbosity=0)

    @classmethod
    def tearDownClass(cls):
        with schema_context(get_public_schema_name()):
            cls.destination.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.child = ChildFactory(id_lagapeo=12345)
        self.activity = ActivityFactory(name="Ski")
        self.source_level = ChildActivityLevel.objects.create(
            child=self.child, activity=self.activity, after_level="A 3B", note="Source"
        )
        with tenant_context(self.destination):
            # Deliberately different primary keys between periods.
            self.target_child = ChildFactory(pk=90001, id_lagapeo=12345)
            self.target_activity = ActivityFactory(pk=90001, name="Ski")

    def run_command(self, **kwargs):
        output = StringIO()
        options = {"source": self.tenant.schema_name, "destination": self.destination.schema_name}
        options.update(kwargs)
        call_command("copy_child_levels", stdout=output, **options)
        return output.getvalue()

    def target_level(self):
        return ChildActivityLevel.objects.get(child=self.target_child, activity=self.target_activity)

    def test_copy_creates_level_and_preserves_source(self):
        self.assertIn("created=1", self.run_command())
        with tenant_context(self.destination):
            level = self.target_level()
            self.assertEqual(level.before_level, "A 3B")
            self.assertEqual(level.after_level, "")
            self.assertEqual(level.note, "")
        self.source_level.refresh_from_db()
        self.assertEqual(self.source_level.after_level, "A 3B")
        self.assertEqual(connection.schema_name, self.tenant.schema_name)

    def test_preserves_existing_value_unless_overwrite(self):
        with tenant_context(self.destination):
            ChildActivityLevel.objects.create(
                child=self.target_child,
                activity=self.target_activity,
                before_level="A 1A",
                after_level="A 4C",
                note="Destination",
            )
        self.assertIn("preserved=1", self.run_command())
        with tenant_context(self.destination):
            self.assertEqual(self.target_level().before_level, "A 1A")
        self.assertIn("updated=1", self.run_command(overwrite=True))
        with tenant_context(self.destination):
            level = self.target_level()
            self.assertEqual((level.before_level, level.after_level, level.note), ("A 3B", "A 4C", "Destination"))

    def test_dry_run_does_not_write(self):
        self.assertIn("created=1", self.run_command(dry_run=True))
        with tenant_context(self.destination):
            self.assertFalse(ChildActivityLevel.objects.exists())

    def test_missing_lagapeo_is_skipped(self):
        self.child.id_lagapeo = None
        self.child.save()
        self.assertIn("unmatched=1", self.run_command())
        with tenant_context(self.destination):
            self.assertFalse(ChildActivityLevel.objects.exists())

    def test_missing_activity_is_skipped(self):
        with tenant_context(self.destination):
            self.target_activity.name = "Snowboard"
            self.target_activity.save()
        self.assertIn("unmatched=1", self.run_command())

    def test_empty_source_level_is_skipped(self):
        self.source_level.after_level = ""
        self.source_level.save()
        self.assertIn("created=0", self.run_command())

    def test_repeated_copy_is_idempotent(self):
        self.run_command()
        self.assertIn("preserved=1", self.run_command())

    def test_destination_must_be_later(self):
        with self.assertRaises(CommandError):
            call_command(
                "copy_child_levels",
                source=self.destination.schema_name,
                destination=self.tenant.schema_name,
                stdout=StringIO(),
            )

    def test_interactive_selection_source_then_destination(self):
        # Only these two test periods are offered, ordered by start date.
        with patch("builtins.input", side_effect=["1", "1"]) as prompt:
            call_command("copy_child_levels", dry_run=True, stdout=StringIO())
        self.assertEqual(prompt.call_count, 2)

    def test_unknown_schema_is_rejected(self):
        with self.assertRaises(CommandError):
            self.run_command(source="unknown")
