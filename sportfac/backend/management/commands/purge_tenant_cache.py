from __future__ import annotations

from typing import Any

from django.core.cache import cache
from django.core.management.base import BaseCommand
from redis import Redis

from backend.models import YearTenant  # ajuste si besoin


class Command(BaseCommand):
    help = "Interactively purge all cache keys for a selected YearTenant."

    def _select_tenant(self) -> YearTenant | None:
        tenants = list(YearTenant.objects.order_by("-start_date", "-end_date", "schema_name"))
        if not tenants:
            self.stdout.write(self.style.ERROR("No YearTenant found."))
            return None

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Select tenant to purge:"))
        for idx, t in enumerate(tenants, start=1):
            prod_flag = " [PROD]" if getattr(t, "is_production", False) else ""
            self.stdout.write(
                f"{idx:>2}. {prod_flag} schema={t.schema_name} "
                f"{t.start_date} → {t.end_date} status={t.status} (id={t.id})"
            )

        while True:
            choice = input("> ").strip().lower()
            if choice in {"q", "quit", "exit", "0", ""}:
                return None
            if choice.isdigit():
                i = int(choice)
                if 1 <= i <= len(tenants):
                    return tenants[i - 1]
            self.stdout.write(self.style.WARNING("Invalid choice, try again."))

    def handle(self, *args: Any, **options: Any) -> None:
        tenant = self._select_tenant()
        if not tenant:
            self.stdout.write(self.style.WARNING("Aborted."))
            return

        # Get raw Redis client from django-redis
        try:
            client: Redis = cache.client.get_client(write=True)  # type: ignore[attr-defined]
        except AttributeError:
            self.stderr.write(self.style.ERROR("This command requires django-redis as the cache backend."))
            return

        pattern = f"{tenant.schema_name}:*"
        self.stdout.write(self.style.HTTP_INFO(f"Pattern: {pattern}"))

        confirm = input(f"Are you sure you want to delete all keys for {tenant.schema_name}? (y/N) ").strip().lower()
        if confirm != "y":
            self.stdout.write(self.style.WARNING("Aborted."))
            return

        count = 0
        for key in client.scan_iter(match=pattern, count=500):
            client.delete(key)
            count += 1

        self.stdout.write(self.style.SUCCESS(f"{count} keys deleted for tenant {tenant.schema_name}."))
