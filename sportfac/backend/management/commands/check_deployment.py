import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Sanity-check a freshly installed/deployed instance's static configuration: "
        "referenced documents actually exist, the theme's template/static directories "
        "are present, and collectstatic has actually been run. Meant to be run by hand "
        "right after installing or updating a tenant instance, before it's live - each "
        "Montreux/Coppet/... deployment is its own separate settings module (see "
        "TECH_DEBT.md), so this checks the one instance manage.py is currently pointed "
        "at, not every tenant at once. Exits non-zero if anything failed, so it can also "
        "gate a deploy script."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop at the first failing check instead of running them all.",
        )

    def handle(self, *args, **options):
        checks = [
            self._check_theme_template_dirs,
            self._check_theme_static_dirs,
            self._check_static_root_collected,
            self._check_additional_instructor_email_documents,
        ]

        failures = 0
        for check in checks:
            ok = check()
            if not ok:
                failures += 1
                if options["fail_fast"]:
                    break

        self.stdout.write("")
        if failures:
            self.stdout.write(self.style.ERROR(f"{failures} check(s) failed."))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("All checks passed."))

    def _ok(self, label):
        self.stdout.write(self.style.SUCCESS(f"  OK    {label}"))

    def _fail(self, label, detail):
        self.stdout.write(self.style.ERROR(f"  FAIL  {label}: {detail}"))

    def _heading(self, title):
        self.stdout.write(self.style.MIGRATE_HEADING(title))

    def _check_theme_template_dirs(self):
        self._heading("Template directories (TEMPLATES[0]['DIRS'])")
        dirs = settings.TEMPLATES[0].get("DIRS", [])
        if not dirs:
            self._fail("template dirs", "TEMPLATES[0]['DIRS'] is empty - no theme configured?")
            return False
        all_ok = True
        for d in dirs:
            if os.path.isdir(d):
                self._ok(d)
            else:
                self._fail(d, "directory does not exist")
                all_ok = False
        return all_ok

    def _check_theme_static_dirs(self):
        self._heading("Static source directories (STATICFILES_DIRS)")
        dirs = getattr(settings, "STATICFILES_DIRS", [])
        if not dirs:
            self._fail("staticfiles dirs", "STATICFILES_DIRS is empty - no theme configured?")
            return False
        all_ok = True
        for d in dirs:
            if os.path.isdir(d):
                self._ok(d)
            else:
                self._fail(d, "directory does not exist")
                all_ok = False
        return all_ok

    def _check_static_root_collected(self):
        self._heading("Collected static files (STATIC_ROOT)")
        root = getattr(settings, "STATIC_ROOT", None)
        if not root:
            self._fail("STATIC_ROOT", "not configured")
            return False
        if not os.path.isdir(root):
            self._fail(root, "directory does not exist - has `collectstatic` ever been run?")
            return False
        if not os.listdir(root):
            self._fail(root, "directory exists but is empty - run `collectstatic`")
            return False
        self._ok(f"{root} (populated)")
        return True

    def _check_additional_instructor_email_documents(self):
        self._heading("Instructor email attachments (KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS)")
        documents = getattr(settings, "KEPCHUP_ADDITIONAL_INSTRUCTOR_EMAIL_DOCUMENTS", [])
        if not documents:
            self._ok("(none configured)")
            return True
        static_root = getattr(settings, "STATIC_ROOT", None) or ""
        all_ok = True
        for doc in documents:
            filepath = os.path.join(static_root, doc)
            if os.path.isfile(filepath):
                self._ok(doc)
            else:
                # This is exactly what mailer.tasks.send_instructors_email checks for
                # before attaching each file - a FAIL here means that task will refuse
                # to send the "course information(s)" email to instructors entirely
                # (logged as a Sentry error there, not just a missing attachment).
                self._fail(doc, f"not found at {filepath}")
                all_ok = False
        return all_ok
