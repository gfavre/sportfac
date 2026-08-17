# Django LTS migration — research notes

Working notes for migrating off Django 3.2 (EOL) to the current Django LTS,
across the 12 tenants in production. Started 2026-08-17. This is a planning
document, not a changelog — update in place as findings evolve, keep the
"Open questions" section honest about what's actually been verified hands-on
vs. researched from package metadata.

See also [`TECH_DEBT.md`](TECH_DEBT.md) for how this fits alongside the other
known debt items.

## Target

**Django 5.2 LTS**, not 4.2. Checked 2026-08-17: Django 4.2 LTS itself reached
end of life on **April 7, 2026** — it's no longer a valid landing point, it's
already unsupported too. Django 5.2 LTS (released April 2025) is supported
until **April 2028**. Note for later: from January 2028 Django moves to an
annual release cycle where every feature release gets 3 years of support
(LTS-equivalent by default going forward), which changes how "pick the LTS"
works after that point — not relevant to this migration, just don't be
surprised by it later.

**Python floor: 3.11+**, not just 3.10. Driven by `tenant-schemas-celery`
5.0.0 (latest as of Aug 2026), which drops Python 3.9 *and* 3.10 support.
`django-tenants` 3.14.0 only requires Python 3.10+, so the stricter
requirement is `tenant-schemas-celery`'s. Pick 3.11 or newer as the target
Python version for the whole migration, not 3.10.

## The two structural packages (multi-tenancy) — the real gating factor

These are the packages the whole app is built on (schema-per-tenant Postgres
+ tenant-aware Celery). If either doesn't have a real Django 5.2 path, nothing
else in this list matters until that's resolved.

### `django-tenants` — looks fine, but a big version jump

- Currently pinned: `django-tenants~=3.3` (`requirements/base.txt`).
- Latest: **3.14.0** (released Aug 5, 2026). Its classifiers list Django 5.2,
  6.0, 6.1 support explicitly — no Django 4.2 classifier anymore on the
  latest release, meaning if a Django 4.2 intermediate hop is used (see
  "Suggested path" below), an *older* django-tenants release compatible with
  4.2 needs to be identified separately, not just jumped straight to 3.14.
- 3.3 → 3.14 is 11 minor versions — **not verified for breaking changes**.
  django-tenants' own CHANGELOG needs a read before assuming this is a
  drop-in bump, even though the Django-version story looks good on paper.
- Requires PostgreSQL 13+ (not checked yet whether prod's Postgres meets this
  — separate thing to verify, unrelated to Django/Python but blocking if not).

### `tenant-schemas-celery` — the actual unknown, needs a hands-on spike

- Currently pinned: `tenant-schemas-celery == 3.0.0`.
- Latest: **5.0.0** (released Aug 1, 2026), requires Python >=3.11 (drops
  3.9/3.10). Explicitly built for `django-tenants` (not the old
  `django-tenant-schemas`) — consistent with what's used here.
- **No Django version classifiers or compatibility statement found** via
  PyPI/GitHub research for this package, at any version. It's a thin wrapper
  around Celery's app class to propagate the current tenant into tasks — low
  surface area, so it *probably* doesn't care much about the Django version
  directly, but "probably" isn't good enough to plan a 12-tenant prod
  migration on. This needs to be verified by actually running it against a
  Django 5.2 app, not by more searching.
- Repo (`maciej-gol/tenant-schemas-celery`) looks maintained but low-traffic
  (infrequent commits, 2 open issues, unread). Worth a skim of those issues
  before starting, in case one of them is exactly "does this work with Django
  5.x".

## Other pinned packages — researched 2026-08-17, Django 5.2 status

All six packages `requirements/base.txt` explicitly pins below their latest
release "unless django is migrated to 4.0" (see `TECH_DEBT.md`) now have a
real Django 5.2 path, **except one**:

| Package | Pinned | Django 5.2 support | Notes |
|---|---|---|---|
| `django-crispy-forms` | 1.14.0 | Yes, in 2.6 (Mar 2026) | 1.x → 2.x is a breaking rewrite (template packs, `Meta` config) — real migration work, not just a version bump, across every form using crispy layout |
| `django-import-export` | 3.0.2 | Yes, in recent 4.x releases | not yet pinned down which exact version to target |
| `django-recaptcha` | 3.0.0 | Yes, 5.0/5.1/5.2 in recent releases | original pin comment already flagged "settings changes needed" — still true |
| `django-admin-sortable2` | 1.0.4 | Yes, in 2.3.1 | |
| `django-phonenumber-field` | 7.0.1 | Yes: 4.2, 5.2, 6.0 | needs Python >=3.10, compatible with the 3.11 floor above |
| `django-anymail` | 11.1 | **Not checked yet** | TODO before starting |
| `djangorestframework-datatables` | 0.5.1 | Likely fine — see below | low-effort verification, not a redesign candidate |

### `djangorestframework-datatables` — revised assessment (2026-08-17, corrected)

Initial read of this (stale-looking PyPI release, no clear classifiers) turned
out to overstate the risk on two counts, both corrected after actually
checking the primary sources instead of just aggregated package-index
summaries:

- **Not actually abandoned.** The upstream repo's `tox.ini` tests explicitly
  against Django 3.2, 4.1, 4.2, 5.0, *and* Django's own `main` branch (i.e.
  the maintainer tracks upcoming Django versions on an ongoing basis, not
  just old pins) — a low release cadence here reflects "doesn't need to
  change" more than "unmaintained." A user report from 2024 also confirms
  the (then-current) 0.7.2 release kept working through the DataTables.js
  2.1 upgrade (a *frontend*-side major version bump) with zero changes needed
  to the Python package itself — only template/CSS adjustments on the DataTables.js
  side. None of this is a confirmed Django 5.2 test run specifically (classifiers
  stop at 5.0), but 5.0→5.2 is a minor-series gap, much smaller than the 3.2→5.x
  jump already being planned — low risk by comparison. Still worth an actual
  install-and-test rather than assuming, just not a redesign trigger on its own.
- **Not actually load-bearing for "the whole API layer."** `sportfac/settings/base.py`
  does set `DatatablesRenderer`/`DatatablesFilterBackend` as the project-wide
  DRF defaults, but grepping actual usage shows only **3 views depend on it**:
  `DashboardFamilyView`, `DashboardInstructorsView`, `DashboardManagersView`
  (all in `api/views/dashboard_views.py`, backing the admin family/instructor/
  manager list pages), plus one custom filter-backend subclass
  (`api/filters.py::DatatablesFilterandPanesBackend`, adds SearchPanes support,
  phone-number search normalization, and choices/date value cleanup on top of
  the library). Every *other* admin list page in the app already uses jQuery
  DataTables in plain **client-side** mode (`bill-list.html`, `registration/list.html`,
  `course/list.html`, `child-list.html`, `restricted-admin-list.html`,
  `absences-table.html`, `payroll_report.html`, ... — no `serverSide`/`ajax`
  config, confirmed by grep) — meaning they have zero dependency on this
  package already, and the pattern to fall back to for the 3 remaining views
  already exists in this exact codebase.
- **If it ever does need dropping** (not currently expected, kept here for
  reference): convert the 3 dashboard views + their templates to the same
  client-side-DataTables pattern the other 8+ admin lists already use — drop
  server-side pagination/filtering, serve the full row set as plain JSON, let
  DataTables sort/filter/paginate in the browser, and let the client-side
  SearchPanes extension compute its own facet counts from the loaded rows
  instead of `get_search_panes()`. Family/instructor/manager counts per tenant
  are in the hundreds-to-low-thousands range (inferred from bill volumes seen
  elsewhere), comfortably within client-side DataTables' range. This is a
  moderate, well-scoped rewrite of 3 views — not "rebuild the API layer" — but
  isn't currently believed necessary based on the above.
  it's a version bump like the others.

## Multi-tenant migration mechanics (schema-per-tenant, 12 prod tenants)

The user's explicit question: how does *migrating*, not just upgrading
packages, work across tenants. What's known vs. what needs verifying:

- django-tenants ships a `migrate_schemas` management command that iterates
  every tenant schema (plus `public`) and runs Django's normal `migrate`
  inside each — this already exists and is presumably already how normal
  (non-major-version) migrations get deployed today across the 12 tenants.
  **Not yet reverified**: whether the command name/flags changed anywhere
  between the currently-pinned 3.3 and the target 3.14ish release — check the
  changelog, don't assume.
- A Django major-version upgrade is not just "run migrate_schemas with new
  code" — Django itself sometimes ships migrations for its own apps
  (`auth`, `admin`, `sessions`, `contenttypes`) on major version bumps, which
  also need to run per-schema. Same mechanism, just confirm it's exercised
  for Django's own migrations too, not only this project's app migrations.
- **Rehearsal plan, not yet executed**: before touching any of the 12 real
  tenants, this should be dry-run against a disposable tenant schema (e.g.
  spin up a throwaway `YearTenant` in a local/staging DB, on the new
  Django/Python/dependency stack, run `migrate_schemas`, run the full test
  suite against it, exercise the actual registration flow manually) — this
  is the actual next hands-on step, not more research.
- Deploy sequencing across 12 separate supervisor-managed processes (each
  tenant is its own gunicorn + celery worker + celery beat, per
  `kepchup_<tenant>.conf`, sharing one venv per tenant per the `PYTHONPATH`/
  venv layout seen in those configs) — needs its own rollout plan (all 12 at
  once vs. staggered, and what "staggered" even means when they share one
  codebase/venv... probably means all-at-once is actually forced, since they
  share a single deployed code+dependency version, not one per tenant). Not
  scoped yet.

## Suggested path (not yet started)

Given this is a 3-major-version jump (3.2 → 4.0/4.1/4.2 → 5.0/5.1/5.2) and
Django's own upgrade docs recommend going one feature release at a time
rather than leaping directly:

1. Land on **Django 4.2 LTS as an intermediate checkpoint first**, even
   though it's also EOL now — it's still the best-trodden path with the most
   migration guides (both Django's own release notes and most of the pinned
   packages' own migration docs are written LTS-to-LTS), and it isolates
   "did the 3.2→4.2 jump break something" from "did the 4.2→5.2 jump break
   something" instead of debugging both at once.
2. Then 4.2 → 5.2 as a second hop.
3. Bump Python to 3.11+ alongside the *first* hop (4.2 already supports
   3.11+, no reason to defer it to the second hop).
4. `djangorestframework-datatables` no longer looks like a blocker (see
   revised assessment above) — a quick smoke test of the 3 dashboard views
   during the 4.2 hop is enough, no separate workstream needed.

## Open questions / next concrete steps

- [ ] Verify `tenant-schemas-celery` actually works against Django 4.2 (then
      5.2) by installing it in a scratch venv and running real tenant-aware
      Celery tasks against it — this is the single most load-bearing unknown.
- [ ] Read django-tenants' CHANGELOG for the 3.3→3.14(ish) range for breaking
      changes, not just the Django-version classifier.
- [ ] Check prod's actual Postgres version against django-tenants' PG13+
      requirement.
- [ ] Check `django-anymail`'s Django 5.2 support (not yet researched).
- [ ] Smoke-test the 3 `djangorestframework-datatables` views
      (`DashboardFamilyView`/`Instructors`/`Managers`) during the 4.2 hop —
      expected to be fine per the revised assessment, just confirm.
- [ ] Rehearse the whole thing against one disposable tenant schema before
      any of the 12 real ones.
- [ ] Scope the deploy sequencing question (single shared venv per tenant
      config means this is probably an all-12-at-once cutover, not
      staggered — confirm this reading of the supervisor configs).
