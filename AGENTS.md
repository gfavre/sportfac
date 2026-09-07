# AGENTS.md

Instructions for Codex and other coding agents working on this repository.

## Project Overview

Kepchup / Sportfac is a Django application for managing school sport activities for children:
activities and courses, family accounts, child registrations, billing, online payments,
attendance, absences, instructor documents, exports, and per-school/year administration.

The stack is Django, Django REST Framework, PostgreSQL, Redis, Celery, django-tenants,
server-rendered Django templates, and legacy AngularJS/jQuery assets.

## Working Directory

Work from the repository root.

The layout is intentionally nested:

- repository root: `sportfac/`
- Django project and apps: `sportfac/`
- Django settings package: `sportfac/sportfac/`

From the repository root, use commands like:

```sh
python sportfac/manage.py ...
```

This matters because `scripts/`, coverage paths, and project tooling assume root-relative paths.

## Environment

The historical local setup uses virtualenvwrapper and a virtualenv under `~/.virtualenvs/`.
Install local dependencies with:

```sh
pip install -r requirements/local.txt
```

Tests use:

```sh
export DJANGO_SETTINGS_MODULE=sportfac.settings.test
export DB_NAME=kepchup
```

The test settings read `DB_NAME` from the environment. If Django cannot import, first check that
the correct virtualenv is active.

## Common Commands

Run the full documented test command from the repository root:

```sh
coverage run --source 'sportfac' sportfac/manage.py test --keepdb --settings=sportfac.settings.test absences activities api appointments backend contact mailer payments payroll profiles registrations schools waiting_slots wizard
```

Run a narrower test module when appropriate:

```sh
python sportfac/manage.py test --keepdb --settings=sportfac.settings.test path.to.tests
```

Run Django checks:

```sh
python sportfac/manage.py check --settings=sportfac.settings.test
```

Run pre-commit on touched files when available:

```sh
pre-commit run --files path/to/file.py path/to/template.html
```

If the local environment cannot run a command, report the exact missing dependency or service.

## Code Standards

Follow `.pre-commit-config.yaml`.

- Black line length is 119.
- isort is configured in `pyproject.toml`; preserve import grouping.
- pyupgrade is configured with `--py311-plus`.
- django-upgrade targets Django 4.1 syntax.
- flake8 uses bugbear, comprehensions, return, implicit string concat, and cognitive complexity.
- Do not add `from collections.abc import Callable`; this repo forbids it. Use `typing.Callable`.
- Keep LF line endings, no trailing whitespace, no debug statements.

Prefer small, causal changes. Do not refactor unrelated code while fixing a bug.

## Testing Expectations

Treat critical business behavior as requiring regression tests. Admin display-only changes can be
validated with lighter checks, but changes affecting registrations, billing, payments, tenant
selection, sessions, permissions, data integrity, imports/exports, Celery tasks, or PDF generation
need focused tests.

Minimum expectations:

- Every changed view should have a smoke test for a successful response (`200`) when accessible.
- Every changed view with authentication or permission behavior should test login redirects,
  forbidden responses, or role-specific access as applicable.
- Every changed model method or property should have direct model tests for the normal path and
  relevant edge cases.
- Every bug fix should include a regression test that would have failed before the fix.
- For performance fixes, prefer query-count or behavior-preserving tests over timing assertions.

Use the project’s existing test helpers and factories before adding new test infrastructure.

## Multi-Tenant Model

Do not assume tenants are different schools.

Each school/city deployment is separate infrastructure with its own database, Redis, settings module,
and theme. Inside one deployment, django-tenants represents school-year periods through
`backend.models.YearTenant`.

Important consequences:

- `Domain.is_current` marks the live production period for that deployment.
- Tenant resolution is session-based through `VersionMiddleware`, not ordinary hostname-based
  django-tenants behavior.
- Users and sessions live in the shared/public schema and persist across periods.
- Migrations and data fixes for tenant apps may need to run across all tenant schemas.
- Be careful with caches before tenant resolution; the current schema may not yet be what the code
  is trying to determine.

Read `docs/architecture-tenants.md` before changing tenant, session, cache, or period-switching code.

## Business-Critical Areas

Be especially conservative around:

- registration creation, cancellation, waiting lists, and course capacity;
- `Course.nb_participants`, `Course.has_waiting_list`, and other denormalized state;
- `Registration`, `Child`, `Bill`/invoice, `Rental`, and payment transaction relationships;
- deleting or soft-deleting users, families, children, registrations, and invoices;
- payment callbacks and invoice status transitions;
- generated PDFs and email attachments;
- tenant switching, current period changes, sessions, and cache invalidation.

Never silently discard manual staff choices such as `Course.allow_new_participants` unless the user
explicitly asks for that behavior.

## Admin Conventions

Use `SportfacModelAdmin` or `SportfacAdminMixin` for Django admin classes unless there is a concrete
reason not to. These project admin helpers intentionally disable admin log writes and provide shared
behavior such as timestamp display.

For timestamped models, expose `created` and `modified` as read-only fields rather than editable
form fields.

## Frontend And Assets

The project still contains legacy AngularJS and jQuery assets.

- `assets/js/` is the source for some legacy frontend bundles.
- `static/js/` contains built output used in production.
- When changing bundled JS, update the built output using the documented project command or explain
  why it could not be rebuilt.
- Be mindful of cache-busting. Several historical incidents involved stale CSS/JS/templates.
- Themes under `sportfac/themes/*/templates/` are full template copies, not lightweight overrides.
  Shared template fixes often need propagation across all themes.

Do not start a broad AngularJS migration unless the user explicitly asks for it. The documented
direction is AngularJS to htmx where it fits, with small vanilla JS islands when needed.

## Dependencies And Upgrades

Django is pinned to `>=3.2.20,<4.0.0` in `requirements/base.txt`, while the formatter/upgrade hooks
prepare code for newer Python/Django syntax. Do not upgrade Django, django-tenants, DRF, or pinned
third-party packages incidentally.

Several requirements explicitly warn not to upgrade before a Django upgrade. Respect those comments.

CKEditor 4 is known EOL but currently staff-only. Do not replace it opportunistically.

## Documentation

Keep `CHANGELOG` entries precise and causal for user-visible fixes, incidents, and meaningful
behavior changes. The existing style favors concrete root cause, consequence, and verification.

When the user asks to commit and bump the version, update `CHANGELOG` using Keep a Changelog
sections (`Added`, `Changed`, `Fixed`, etc.) and keep each bullet concise, ideally one or two
sentences. Also update the package version in `sportfac/sportfac/__init__.py`; `__version__` must
match the new changelog version.

Update `TECH_DEBT.md` when resolving or discovering durable technical debt that future agents should
not need to rediscover.

For incident-prone areas, prefer adding short local comments only where they prevent reintroducing a
known bug.

## Data And Operations

Be careful with management commands and scripts that mutate tenant data.

- Prefer dry-run or non-destructive modes when available.
- Confirm which tenant/schema is targeted.
- Do not write migrations unless the task requires schema or data migration changes.
- Do not run destructive commands or delete data without explicit user approval.

For deployment sanity checks, see `manage.py check_deployment`.

## Collaboration

Act as a senior Python/Django developer:

- read the surrounding code before editing;
- preserve existing project patterns;
- explain assumptions and validation clearly;
- challenge unclear or risky requests with concrete reasons;
- keep changes scoped to the requested behavior;
- leave unrelated dirty worktree changes alone.
