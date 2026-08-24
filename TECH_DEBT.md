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
- Concrete cost of the duplication, observed 2026-08-17/18: whether a course is
  open to "any age"/"any school year" (i.e. `age_min`/`age_max` or
  `schoolyear_min`/`schoolyear_max` all unset) is a single business rule, but
  it was independently reimplemented in **four** places - the wizard's
  AngularJS calendar (`activities/controllers.js`), its separate click-time
  gate (`activities/services.js`'s `Child.canRegister()`), the API's
  `RegistrationSerializer.validate()`, and the backend admin's own course
  dropdown (`backend/forms.py`'s `CourseSelectMixin`). All four had the same
  "unrestricted means null, and null compares false/excludes-via-SQL-NULL
  instead of meaning open to everyone" bug, found and fixed one at a time over
  two days because no existing test anywhere covered the *unrestricted* case -
  only the "has a restriction, is the child in/out of range" case was tested,
  in each of the four places separately. This is the concrete failure mode a
  single source of truth (backend-only eligibility, with the frontend just
  rendering/consuming it) would have prevented: one bug, one fix, one test,
  instead of four of each.

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

## Django 3.2 (past EOL)

- Pinned in `requirements/base.txt`: `django >=3.2.20,<4.0.0`.
- Django 3.2 is the last LTS before the current one; its security support window
  has closed. Running an unsupported major version with no further security
  patches from upstream.
- Several third-party packages are **deliberately pinned below their latest
  release**, with explicit comments in `requirements/base.txt` tying the pin to
  this Django version. These are the concrete blockers/prerequisites for a
  Django 4.0+ upgrade, already identified by whoever pinned them:
  - `djangorestframework-datatables==0.5.1` (not 0.7.0)
  - `django-anymail~=11.1` (not 12.0)
  - `django-recaptcha==3.0.0` (not 4.0 — also needs settings changes)
  - `django-crispy-forms==1.14.0` (not 2.0 — also needs requirements changes)
  - `django-admin-sortable2==1.0.4` (not 2.0)
  - `django-import-export==3.0.2` (not 4.0)
  - `django-phonenumber-field==7.0.1` (needs Django 4.2+ specifically, not just 4.0)
- Not yet audited for this list: `django-tenants~=3.3` (multi-tenancy, the most
  structurally load-bearing dependency in the project — compatibility here is
  probably the real gating factor for the whole upgrade), `tenant_schemas_celery`,
  `django-ckeditor`, `django-select2`, `django-floppyforms`, `django-sekizai`,
  `django-dbtemplates`, `django-localflavor`. Check each against the target
  Django version before starting.
- **Before scoping the upgrade**: check django-tenants' own supported Django
  range first — it likely determines which Django version is even reachable in
  one hop (3.2 → 4.2 LTS is probably the sane target, not 3.2 → 5.x directly).

## Python 3.9 (past EOL)

- Local dev venv and (per `kepchup_*` supervisor configs) production both run
  Python 3.9 (`/home/greg/.virtualenvs/kepchup_*`, `/Users/grfavre/.pyenv/versions/3.9.1`).
  Python 3.9's security support window has also closed.
- Tied to the Django upgrade in practice: bumping Python is low-risk on its own,
  but the real motivation to do it now is doing both together (a Django 4.2
  upgrade needs Python 3.10+ anyway), rather than two separate migration/testing
  cycles.

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

## Registration-opening performance backlog

Found by analyzing the production access log for the 2026-08-18 Montreux
registration opening (44,180 requests, 8am rush). Full breakdown (traffic
share by flow, session types, ranked-by-total-server-time chart) published
as an artifact; this entry keeps the still-open findings in the repo so
they don't only live in a chat log. Several related items from this same
analysis are already fixed — see the CHANGELOG's Unreleased section.

- **`/api/dashboard/users/` fired 5× with identical params within about one
  second** in one admin session trace (08:54:55-56) — looks like a
  duplicated client-side fetch (e.g. an effect re-running) rather than a
  real need to refresh 5×. Avg latency 482ms × the 5x multiplier makes this
  worth deduplicating (stable query key / request dedup) before touching the
  endpoint itself.
- `InstructorMixin` (`activities/views.py`, used by `MailCourseInstructorsView`
  and others) has the same bare-`get_object()`/double-fetch pattern that was
  fixed on `CourseAccessMixin` (see CHANGELOG) — worth the same treatment if
  those views show up slow.

## Local `TenantTestCase` suite is currently broken (`cache.delete_pattern`)

Found 2026-08-18 while writing/running the session-replay tests above.
`backend/signals.py:11`'s `clear_tenant_cache()` (wired to `YearTenant`'s
`post_save`/`post_delete`, so it fires on every `TenantTestCase` tenant
setup) calls `cache.delete_pattern("tenants_context_user_*")` — a
`django-redis`-only method, already flagged as such by an existing comment
on that line (`# ⚠️ selon backend, si Redis -> tu peux utiliser
cache.delete_pattern`). `sportfac/settings/test.py:41` configures
`django.core.cache.backends.locmem.LocMemCache`, which has no
`delete_pattern` — so `setUpClass` raises for **every** `TenantTestCase` in
the repo, confirmed by running the pre-existing `wizard/tests/test_views.py`
and `test_workflow.py`, not just new tests. Also needs `DB_NAME=kepchup`
set locally (peer-auth Postgres) to get past the settings import at all.
Not yet fixed — either switch `CACHES["default"]` in `settings/test.py` to
`django-redis` (if a local Redis is an acceptable test dependency) or guard
`_invalidate_all_tenant_caches()` to no-op / fall back to `cache.clear()`
when the configured backend doesn't support `delete_pattern`.

## Per-tenant behavior flags hardcoded in settings.py instead of dynamic_preferences

Several `KEPCHUP_*` flags that control per-tenant *business* behavior (not
infrastructure) live as plain Python constants in each tenant's
`sportfac/settings/<tenant>.py`, rather than as `dynamic_preferences` entries
(`backend/dynamic_preferences_registry.py`) editable from the backend admin at
runtime. Concretely: only a developer can change them, and every change needs
a code deploy - not viable for anything time-sensitive (e.g. mid-rush, as
happened 2026-08-22 for Jorat, see below).

- Prompted by `KEPCHUP_ACTIVITIES_CAN_REGISTER_SAME_ACTIVITY_TWICE`
  (`sportfac/settings/base.py`, overridden per tenant): controls whether a
  child can register to more than one course within the same activity
  (enforced client-side in the wizard's calendar,
  `assets/js/activities/controllers.js`'s `updateAvailableEvents`). Jorat asked
  to flip it (`False` → `True`) *during* their registration opening, 2026-08-22,
  after a course filled in 4 minutes - had to be done as an emergency settings
  change + deploy, exactly the kind of situation this flag's home (`settings.py`
  vs. an admin-editable preference) makes unnecessarily risky.
- Not an isolated case - `KEPCHUP_LIMIT_BY_AGE`/`KEPCHUP_LIMIT_BY_SCHOOL_YEAR`,
  `KEPCHUP_MAX_REGISTRATIONS`-adjacent flags, and others in
  `sportfac/settings/base.py` follow the same pattern. `MAX_REGISTRATIONS`
  itself is the counter-example already done right: it's a
  `dynamic_preferences` `IntegerPreference`
  (`backend/dynamic_preferences_registry.py`), editable per tenant from the
  admin, no deploy needed.
- Not yet fixed. Migrating a flag means: adding it to
  `dynamic_preferences_registry.py`, updating every read site to go through
  `global_preferences_registry.manager()[...]` instead of `settings.KEPCHUP_*`,
  and deciding a sensible default per existing tenant (since the settings.py
  values would otherwise silently reset to the new preference's default on
  migration). Worth doing for `CAN_REGISTER_SAME_ACTIVITY_TWICE` first, given
  it just caused a real incident.

## Static assets have no cache-busting, and `base.html` is duplicated 15×

Found 2026-08-23: after deploying 4.6.5 to Oron, a normal reload showed
FullCalendar's own default event color instead of the new hatched-green
"sibling" style — the new JS had loaded (its `<script>` tag is
`app.min.js?v={{ VERSION }}`, so a version bump forces a fresh fetch) but the
browser served its *cached* `style.css`, which has no such query string and
therefore never changes URL between deploys (`STATICFILES_STORAGE` is plain
`django.contrib.staticfiles.storage.StaticFilesStorage` — no content hashing).
Fixed for `style.css`/`not_production.css` in 4.6.6 by adding `?v={{ VERSION
}}` everywhere, but two structural issues remain:

- **No systemic fix, only this one file.** `montreux_epa`/`montreux_passvac`
  already had this exact `?v={{ VERSION }}` patch on `style.css` from an
  earlier, unrecorded incident — it was never propagated to the other 13
  themes (which is exactly how Oron got bitten this time). Per-theme CSS
  (`coppet.css`, `oron.css`, `vevey.css`, ...) has the identical unversioned-URL
  problem and hasn't been touched at all. Every future static asset added the
  same way will have the same bug unless someone remembers to version it by
  hand, every time, in every theme.
- **Same bug, found again the same day, in JS-fetched HTML partials**:
  `activities/controllers.js`'s `$modal({template: ...})` for
  `static/partials/activity-detail.html` had no versioning at all (found by
  personally hitting it — added a new hint below "Places disponibles",
  invisible until a hard reload); `activities/app.js`'s `$routeProvider` for
  `activity-list.html` had a *hand-maintained* `?v=3` counter, only
  cache-busting when a developer remembered to bump it on a template change.
  Both fixed 2026-08-23 by introducing `window.KEPCHUP_VERSION` (set from
  `{{ VERSION }}` in `activities_app.html`, read by both call sites) — but
  that's now a **third** distinct hand-rolled cache-busting mechanism in this
  codebase (`?id={{ timestamp }}` for `DEBUG`, `?v={{ VERSION }}` in Django
  templates, `?v=${window.KEPCHUP_VERSION}` for JS-side fetches), each
  requiring a developer to remember to apply it to every new static
  reference. Strengthens the case for option 1 below over option 2 - a
  systemic fix would make all three unnecessary.
- **`themes/*/templates/base.html` (14 files) and `templates/base.html` are
  full copies, not `{% extends %}` + block overrides.** Any fix to the shared
  layout (this cache-busting fix included) has to be hand-applied to all 15
  files. Easy to miss one (see above) and easy for the copies to drift apart
  over time regardless.

Two independent, non-exclusive fixes discussed 2026-08-23, neither started:

1. **Switch to `ManifestStaticFilesStorage`** (or equivalent hashed storage):
   Django content-hashes every static file's URL automatically on
   `collectstatic`, solving this for *every* asset, forever, with no
   per-template query string to remember. Real fix, but bigger and riskier to
   land: several of these templates use `{{ STATIC_URL }}css/style.css` (raw
   string concatenation) rather than `{% static %}` — hashed storage only
   rewrites URLs generated *through* `{% static %}`/`static()`, so those call
   sites would need converting too, or they'd silently keep serving
   unhashed/stale URLs. `ManifestStaticFilesStorage` is also strict by default
   and can fail `collectstatic` outright on any broken asset reference (e.g. a
   `url(...)` in a CSS file pointing at a missing file) — needs a trial
   `collectstatic` run to find those before switching in production.
2. **Extract the shared `<head>` static-asset block** (or more of `base.html`)
   into one `{% include %}`d partial reused by all 15 `base.html` variants, so
   a future fix (cache-busting or anything else) is a one-file change instead
   of 15. Smaller, lower-risk, doesn't depend on (1) and could land first.

No regression test currently guards against a theme missing the `?v=`
query string — worth adding one (independent of which fix above is chosen)
so a future drift is caught before deploy rather than after, the way this one
was.

## PhantomJsCloud - external PDF rendering dependency, replace everywhere

Found 2026-08-24 while auditing Celery `rate_limit` coverage after the bill-PDF
burst issue below. `registrations/pdf.py` (bill PDFs, QR-invoice compositing)
already generates PDFs locally via Playwright (`sync_playwright`,
`chromium.launch()`) - but two other, older code paths still ship their HTML
off to `PhantomJsCloud.com` (`settings.PHANTOMJSCLOUD_APIKEY`, a paid external
API) instead:

- `mailer/pdfutils.py`'s `PDFRenderer.render_to_pdf` (base class for
  `CourseParticipants`, `CourseParticipantsPresence`, `MyCourses`,
  `InvoiceRenderer`) - used by `mailer.tasks.send_instructors_email` (backend
  "mail instructors" action: participants list, decompte, presence list,
  "my courses" attachments).
- `activities/views.py`'s `PaySlipDetailView.pdf()` (`?pdf=1` on
  `activities:payslip-detail`, a UUID-keyed URL, presumably instructor
  payslips reached via an emailed link) - a **synchronous, in-request** HTTP
  call to PhantomJsCloud, not even behind Celery, so it ties up a web worker
  for the external call's full duration too.

Two separate, non-exclusive reasons to migrate both onto the same local
Playwright approach `registrations/pdf.py` already uses: drop the external
paid dependency, and stop maintaining two different PDF-rendering code paths
for what's fundamentally the same problem.

**Careful about CPU if/when this is done**: local Playwright is real CPU/memory
cost on the same box as the web server (see the `rate_limit` entry right
below - `send_bill_pdf_email`/`generate_invoice_pdf` are throttled to `12/m`
specifically because of this). That said, this is lower urgency than the bill
case: `send_instructors_email` is admin-triggered (one admin, one click, not
hundreds of parents landing on the same page after a registration rush), and
`PaySlipDetailView` is presumably one instructor at a time via their own
emailed link - burst risk here is real but far smaller in scale. Still worth
a `rate_limit` (or at least a look at expected concurrent volume) once this
moves to local rendering, rather than assuming "admin-only" means "no burst
possible."

## Performance work already done (2026-08, for reference — not debt)

Not tech debt, but context for anyone reading this file wondering what's already
been addressed on the "site slow during registration rush" front: `ActivityViewSet`
structural caching, course-capacity race condition (`select_for_update`), N+1
fixes in absence creation/deletion and Bill total/payment cascades, and
rate-limited async PDF generation for bill confirmation emails. See CHANGELOG
4.5.0/4.5.1 entries and git log for detail if revisiting this area.
