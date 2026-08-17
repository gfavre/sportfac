# Technical debt

Living list of known technical debt for the sportfac/Kepchup project. Not a task
tracker — just a reference so decisions and their context aren't re-derived from
scratch each time. Update in place as items are resolved or new ones are found.

## AngularJS 1.x → htmx (medium-term goal)

- AngularJS 1.x reached end-of-life in January 2022 (no more security patches
  upstream) and the whole framework generation it belongs to is long out of
  favor. Direction decided: migrate off it, htmx preferred, Vue as fallback if
  htmx turns out not to fit a given piece.
- Current AngularJS surface, under `assets/js/` (gitignored — source of truth
  for the front-end build; `static/js/` holds the tracked, built output served
  in prod, see `activities_app.html`'s `{% if debug %}`/`{% else %}` script
  tags for how the two are wired):
  - `children/` (app.js/controllers.js/services.js/directives.js/filters.js,
    ~420 lines) — the family's "manage my children" app. Smallest, self-
    contained Angular module — the suggested starting point, matches the
    stated intent.
  - `activities/` (~970 lines) — the registration wizard's activity/course
    picker and weekly calendar (`ui-calendar` wrapping `fullcalendar` 4,
    `Course.toEvents()` etc. — see the LTDP calendar bugs fixed 2026-08-17 for
    a sense of how this module works). The biggest and most interactive piece:
    drag-free but still a live, clickable weekly agenda grid built from
    dynamically fetched course/registration data. This is the one where a
    plain htmx swap-on-click model may not be a clean fit for the calendar
    widget specifically — likely means either keeping a small vanilla-JS/
    fullcalendar island for just the grid while htmx-ifying the surrounding
    page (activity list, selection, forms), or evaluating whether fullcalendar
    itself (vanilla, no Angular wrapper needed) is still the right calendar
    lib. Worth spiking before committing to an approach here.
  - `extra/` (~230 lines) — extra/complementary questions on registration,
    tied into the same wizard flow as `activities/`; probably migrate together
    with it rather than as its own separate step.
  - `assets/js/backend/*.js` is already plain jQuery, not Angular — not part
    of this migration.
  - Vendor footprint that becomes removable once fully migrated: `angular.js`
    itself plus `angular-route`, `angular-cookies`, `angular-sanitize`,
    `angular-ui-calendar`, `angularstrap` (+ its templates) — all currently
    bundled into `static/js/activities/app.min.js` and `static/js/children/
    app.min.js` per-page.
- No work started yet. This entry exists to record the direction/priority
  order (children first, activities+extra after, backend jQuery untouched) so
  it doesn't need re-deciding later.

## `Bill` → `Invoice` rename, half-done

- The model is called `Bill` (`registrations.models.Bill`), but the intent going
  forward is `Invoice` everywhere — that's the desired end state, not a
  preference to weigh against keeping `Bill`.
- Already partially done: `payments.DatatransTransaction.invoice` and
  `payments.PostfinanceTransaction.invoice`, and `appointments.Rental.invoice`,
  are already named `invoice` (FK to the `Bill` model). Two views alias the
  import at the top of the file — `from registrations.models import Bill as
  Invoice` (`wizard/views.py:17`, `registrations/views/wizard.py:23`) — so
  variables/context keys read as `invoice` downstream even though the class is
  still `Bill`.
- Not yet renamed (as of 2026-08-17, rough counts):
  - The model class itself: `registrations.models.Bill` (+ `BillManager`).
  - `Registration.bill` — the FK field name itself is still `bill`, inconsistent
    with `payments`/`appointments` above which already say `invoice`.
  - ~19 Python files still reference `Bill` directly (views, forms, admin,
    tasks, serializers — outside migrations/tests).
  - ~19 templates use `bill`/`Bill` in variable names or IDs (~17 already use
    `invoice`/`Invoice` in places, confirming the mixed state).
  - URL names/paths in `backend/urls.py`: `bills`, `bill-list`, `bill-detail`,
    `bill-pdf`, `bill-update`, `bill-export`.
- No `db_table` override on `Bill`'s `Meta` — it uses Django's default table
  name (`registrations_bill`). Renaming the model class to `Invoice` means a
  `RenameModel` migration (`ALTER TABLE RENAME`, generally safe/cheap on
  Postgres) — but it has to run across **every tenant schema** (django-tenants,
  schema-per-tenant), not just `public`, so plan the migration/deploy step
  accordingly rather than assuming a single-schema `migrate` run covers it.
- Suggested order if/when this gets picked up: rename the FK field
  (`Registration.bill` → `Registration.invoice`) and the model class together in
  one migration, then sweep views/forms/admin/serializers, then templates, then
  URL names last (URL name changes need `reverse()`/`{% url %}` call sites
  updated everywhere, easy to miss one).

## Triple-nested project layout forces repo-root invocation

- The repo root, the Django project directory, and the settings package are all
  literally named `sportfac`, nested three deep:
  `sportfac/` (repo root) → `sportfac/sportfac/` (Django project dir, holds
  `manage.py` and all the apps: `activities/`, `registrations/`, etc.) →
  `sportfac/sportfac/sportfac/` (the actual `sportfac` Python package: settings,
  urls, wsgi, celery app, `__init__.py`/`__version__`).
- `manage.py` itself doesn't care about CWD (Python auto-adds a script's own
  directory to `sys.path`, so `python manage.py ...` works whether you run it
  from the Django project dir or invoke `python sportfac/manage.py ...` from
  the repo root). The actual friction is everything *around* it:
  - `scripts/` (ad-hoc one-off maintenance scripts, e.g. `assign_instructors.py`,
    meant to be piped into `manage.py shell`) lives as a **sibling** of the
    Django project dir, at the repo root — not inside it. Referencing both
    `manage.py` and a script in the same command only works cleanly from the
    repo root (`python sportfac/manage.py shell < scripts/foo.py`); cd'ing into
    the Django project dir first breaks the relative path to `scripts/`.
  - `setup.cfg`'s `[coverage:run]` include paths are written with a `sportfac/`
    prefix (`sportfac/activities`, `sportfac/registrations`, ...), i.e. relative
    to the repo root, not to the Django project dir — coverage tooling silently
    assumes repo-root invocation too.
  - Likely other tooling (Makefile-driven docs build, CI config, `.idea` run
    configs) makes the same assumption; not fully audited.
- No decision made on fixing this. A real fix (renaming one or more of the three
  `sportfac` levels, or moving `scripts/` inside the Django project dir) touches
  imports, deploy scripts (`PYTHONPATH=.../kepchup_coppet/sportfac` in every
  supervisor config), and CI — high blast radius for a convenience fix. Lower
  effort mitigation: document the "always invoke from repo root" convention
  explicitly (e.g. a root-level Makefile target) rather than restructuring.

## Django 3.2 + Python 3.9 (both past EOL)

- Pinned in `requirements/base.txt`: `django >=3.2.20,<4.0.0`. Local/prod both
  run Python 3.9. Both are past their security-support window — the one item
  in this whole file where time passing actively makes things worse (see the
  2026-08-17 discussion below), not just "annoying to work with."
- **Active research and planning has started** — see
  [`DJANGO_LTS_MIGRATION.md`](DJANGO_LTS_MIGRATION.md) for the up-to-date
  findings (target versions, per-package Django 5.2 compatibility research,
  the multi-tenant migration mechanics, and the current open questions/next
  steps). Don't duplicate that detail here — this entry is just the pointer.
- Gravity assessment (2026-08-17): 12 tenants share one VM and one codebase —
  a Django/Python CVE isn't 12 independent risks, it's one risk with a 12x
  (or more, given other unrelated apps share the same box) blast radius. The
  system handles real family/payment data (IBAN, addresses, children's birth
  dates), raising the stakes of any compromise. Not "actively being
  exploited" — no evidence of that — but the risk compounds with time in a
  way the other items in this file don't, hence prioritizing it over the
  others.

## CKEditor 4 (EOL, `ckeditor.W001` system check warning)

- `django-ckeditor==6.7.2` bundles CKEditor 4.22.1 by default, which is
  end-of-life with unpatched security issues (surfaces as a Django system check
  warning on every `manage.py` run).
- Actual exposure is lower than it looks: every usage in this codebase is
  **backend/staff-only**, never a public-facing input field. Grep for
  `RichTextField`/`RichTextUploadingField`/`CKEditorUploadingWidget`:
  - `activities.Activity.informations` / `.description`
  - `activities.Course.comments`
  - `wizard` step description
  - `mailer` model help_text
  - custom widget in `backend/forms.py:576`
- Options considered (2026-08-17):
  1. Do nothing — defensible given staff-only exposure, but the warning stays.
  2. Silence the check (`SILENCED_SYSTEM_CHECKS`) — stops the noise, fixes nothing.
  3. Migrate to CKEditor 5 (`django-ckeditor-5`, separately maintained package) —
     the real fix. Real effort: touches the 4+ fields above, needs verification
     that HTML already stored in the DB (authored with CKEditor 4) still
     displays/edits correctly under CKEditor 5, and CKEditor 5's license terms
     need checking for this use case before committing to it.
  4. Buy CKEditor 4 LTS — avoids a code migration, ongoing cost for an
     internal-only tool; rarely the right call here.
  - No decision made yet; leaning toward deferring (option 1) until there's
    spare capacity, given the low actual exposure.

## Performance work already done (2026-08, for reference — not debt)

Not tech debt, but context for anyone reading this file wondering what's already
been addressed on the "site slow during registration rush" front: `ActivityViewSet`
structural caching, course-capacity race condition (`select_for_update`), N+1
fixes in absence creation/deletion and Bill total/payment cascades, and
rate-limited async PDF generation for bill confirmation emails. See CHANGELOG
4.5.0/4.5.1 entries and git log for detail if revisiting this area.
