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

## Registration-opening traffic analysis (2026-08-18) — performance backlog

Found by analyzing the production access log for the 2026-08-18 Montreux
registration opening (44,180 requests, 8am rush). Full breakdown (traffic
share by flow, session types, ranked-by-total-server-time chart) published as
an artifact; this entry keeps the actionable findings in the repo so they
don't only live in a chat log. Ranked by total-server-time impact
(volume × latency), not raw latency alone — a cheap endpoint called
thousands of times can outweigh a rare slow one.

- **`ChildListView` (`backend/views/user_views.py:309`), served at
  `/backend/child/`, took 4.2-5.9s on every single one of 21 sampled loads**
  (flat regardless of time of day/load — not a concurrency artifact,
  structural). Two compounding causes: the queryset had no `paginate_by` and
  no scoping (full manager sees every `Child` row ever created), and the
  template called `reverse()` up to 5× per row to build the action buttons —
  DataTables only paginated client-side, so the full HTML table was built
  server-side before any paging happened.
  **Fixed 2026-08-18**: converted to the same server-side DataTables pattern
  already used for the user list (`UserListView`/`DashboardFamilyView`) —
  `ChildListView` now renders an empty table shell
  (`get_queryset` returns `Child.objects.none()`), and rows are loaded via a
  new `ChildDatatableSerializer` + `DashboardChildrenView`
  (`api/views/dashboard_views.py`, `api:all_children`) using
  `DatatablesPageNumberPagination`/`DatatablesFilterandPanesBackend` for
  real pagination, sorting and search (including a search pane on
  `is_blacklisted`). Also fixed a latent bug found while rewriting the
  template: the emergency-number `tel:` link referenced
  `registration.child.emergency_number` (undefined in this list context, so
  the link was always empty) instead of the row's own `child`. Verified with
  a real DB-backed request (paginated JSON shape, dotted `name` → ORM
  `__` lookup resolution, actions gating by `is_full_manager`) — not yet
  eyeballed in an actual browser, so a manual smoke test of `/backend/child/`
  (sorting, search, search pane, blacklisted row styling) is still worth
  doing before considering this fully closed.
  `GET /backend/registrations/` (1.1s avg, 21 hits) looks like the same
  symptom family and hasn't been touched — worth checking with the same lens.
- **`/api/courses/<id>/` is the single biggest total-server-time consumer**:
  331.6s cumulative across 6,409 calls, ~52ms each. This is *not* an
  uncached-endpoint problem — `CourseViewSet.retrieve()`
  (`api/views/activities_views.py:171-179`) already caches each course by
  its own key (`tenant_{pk}_course_{id}`), correctly invalidated on write
  by `activities/signals.py` (`course_post_save_invalidate_cache` etc.,
  including on the `nb_participants` update a new registration triggers —
  not filtered out the way the separate structural-activities cache
  deliberately is). So a naive fix — collapsing calls into
  `/api/courses/?ids=1,2,3,...` and caching *that* combined response as one
  blob — would be a regression: it replaces one stable cache entry per
  course with one entry per distinct ID-combination a client happens to
  request, which is a near-certain cache-miss generator.
  **The actual problem is request *count* under concurrency, not per-request
  cost.** Production runs `gunicorn --workers=8 --worker-class=gthread
  --threads=2 --timeout=30` (per the montreux instance's launch command;
  `config/gunicorn.conf`'s generic template was missing `--worker-class`
  entirely — fixed 2026-08-18, template now carries `--worker-class=gthread
  --threads=2 --timeout=30 --max-requests=500 --max-requests-jitter=50` to
  match, `--workers` stays the existing per-instance `%(nb_web_workers)s`
  var) — a **hard ceiling of 8×2=16 concurrent in-flight requests,
  site-wide**, since each
  worker/thread blocks for a request's whole lifecycle (django-tenants
  schema resolution + middleware + view + response) regardless of how cheap
  the underlying cache hit is. Checked directly against this log: one
  single second (06:00:29, i.e. 08:00:29 local, right at the registration
  opening) had **47 requests arrive** — nearly 3× capacity — and 237
  separate one-second windows that day saw ≥16 simultaneous arrivals. Session
  traces show the wizard's activities-step SPA firing **4-5 parallel**
  `/api/courses/<id>/` requests per polling tick per active user (e.g. 4 in
  the same second at 10:39:54 in one trace), so N concurrently-registering
  users generate roughly 4-5×N simultaneous in-flight requests against a
  16-slot ceiling — consistent with the reported "fine at 250 concurrent
  registrants, collapses around 400" behavior (a fixed-capacity ceiling
  degrades flat-then-cliff as utilization→1, not gradually like a
  saturating CPU/DB resource). Caveat: this log only shows 8 scattered `502`s
  that day (not a sustained storm), so it corroborates the mechanism without
  proving a full collapse happened on 2026-08-18 specifically — the
  6:00:29-adjacent latency spikes on otherwise-fast endpoints (`/client/`
  max 4896ms vs 171ms avg, `/api/family/` max 2890ms vs 58ms avg, `/api/
  activities/` max 2801ms vs 61ms avg) are consistent with brief queueing
  against that ceiling. (Ruled out as a competing explanation: the absolute
  worst latencies in the raw log, 60-73s, turned out to be a large static
  PDF brochure — slow client downloads nginx serves directly, not a gunicorn
  worker cost, and `/backend/child/`'s 4-6s is flat at every hour of the
  day including quiet periods, confirming it's the separate structural bug
  above, not queueing.)
  **Fixed 2026-08-18.** Backend: `CourseViewSet.batch` action
  (`api/views/activities_views.py`, `GET /api/courses/batch/?ids=1,2,3`) does
  N individual `cache.get_many`/`cache.set` lookups against the same
  `tenant_{pk}_course_{id}` keys `retrieve()` already uses, and returns them
  combined in one response — same cache granularity/invalidation as today.
  Verified against a real DB: correct ordering, cache reused across
  `retrieve()`/`batch()`, invalidated on `Course.save()`, missing/malformed
  ids handled without a 500. Frontend: `ActivityTimelineCtrl`'s three
  per-course-request loops (`static/js/activities/controllers.js`,
  `updateAvailableEvents`/`updateRegisteredEvents`/`updateOthersEvents`) now
  collect the ids they need and call one new `CoursesService.getMany()`
  (`static/js/activities/services.js`) instead of firing `CoursesService.get()`
  once per course/registration; dispatch logic (available vs unavailable,
  valid vs waiting, which child) is unchanged, just resolved from the batched
  response instead of N independent promises. `app.min.js` rebuilt with the
  exact command documented in `activities_app.html`'s comment. Verified:
  Python side (397 tests, full suite), JS syntax (`node -c`) on both source
  files and the rebuilt bundle, and the new batch endpoint end-to-end via a
  real DB-backed request. **Not verified**: actual rendering in a browser
  (no browser available in the session that made this change) — the
  `activityRegistered`/`overlapping` classification in `updateAvailableEvents`
  has a pre-existing iteration-order dependency that was deliberately
  preserved as-is (computed synchronously before the batched fetch, same as
  before), but a manual smoke test of the wizard's activities step (switch
  between activities, register, confirm the weekly calendar still renders
  and colors courses correctly) is still owed before trusting this fully
  under live load.
- **`/api/dashboard/users/` fired 5× with identical params within about one
  second** in one admin session trace (08:54:55-56) — looks like a
  duplicated client-side fetch (e.g. an effect re-running) rather than a
  real need to refresh 5×. Avg latency 482ms × the 5x multiplier makes this
  worth deduplicating (stable query key / request dedup) before touching the
  endpoint itself.
- **`/activities/courses/<id>/` averaged 438ms** (265 hits that day).
  **Correction**: this was originally mischaracterized above as "public,
  anonymous, effectively-static" — it's actually `MyCourseDetailView`
  (`activities/views.py`), login-required and per-user (visible to a
  course's instructors, or a family with a child registered to it), so
  `cache_page` was never the right fix. **Fixed 2026-08-18** — the real
  cause, found by checking every relation the template
  (`activities/templates/activities/course_detail.html`) touches against
  what was actually prefetched:
  - `CourseAccessMixin.get_object()` (`activities/views.py`) did a bare
    `get_object_or_404(Course, pk=pk)` with no `select_related`/
    `prefetch_related` at all — which **completely overrode**
    `MyCourseDetailView.queryset`'s carefully-set-up prefetching, since
    `UserPassesTestMixin`'s permission check (`test_func`) and the view's
    own render path both call `get_object()`, and this override shadowed
    the subclass's queryset entirely. The intended prefetching was dead
    code; every relation in the template hit the DB fresh, and the course
    was fetched from scratch **twice** per request (once for the
    permission check, once for rendering).
  - `test_func()` itself did `user in [p.child.family for p in
    course.participants.all()]` — fetching every participant (unprefetched)
    then `.child` and `.child.family` per participant in Python: 1+2N
    queries just to decide access, on **every** request, N+1 by
    construction.
  - The template also reads `registration.child.teacher.full_name` (shown
    to non-instructor viewers specifically, i.e. exactly the families this
    access check was already expensive for) and, when `CHILD_SCHOOL` is on,
    `registration.child.school_name` (reads `.school`) — neither was in the
    prefetch list, two more per-participant N+1s.
  Fix: `get_object()` now caches the fetched object on `self` and sources it
  from `self.get_queryset()` when the subclass defines one (falls back to
  `Course.objects.all()` for non-`DetailView` subclasses like
  `MailUsersView`), so the course is fetched once, through whatever
  optimized queryset the subclass declares. `test_func()`'s membership
  check is now `course.participants.filter(child__family=user).exists()` —
  one query regardless of participant count. `MyCourseDetailView.queryset`
  gained `participants__child__teacher`, `participants__child__school`, and
  `sessions` to the existing prefetch list. Verified with a real query-count
  test (`activities/tests/test_views.py::test_query_count_does_not_scale_with_participants`,
  added as a permanent regression test): **0 extra queries between 2 and 25
  participants** on a warmed-up run (both landed at 42; an unwarmed first
  call pays ~120 queries of one-time tenant/preferences/db-template
  bootstrap cost, unrelated to this view — worth knowing if this pattern
  gets reused as a template for measuring other views). Full `api`/
  `activities`/`wizard`/`backend` suite passes (399 tests).
  **Not fixed, same bug shape, out of scope for now**: `InstructorMixin`
  (`activities/views.py`, used by `MailCourseInstructorsView` and others)
  has the identical bare unoptimized/double-fetching `get_object()` pattern
  — worth the same treatment if those views show up slow.

No decisions made yet on any of these; recorded here so the next person
tackling "site slow during registration rush" (see performance work below)
doesn't have to re-derive them from the raw log.

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

## Performance work already done (2026-08, for reference — not debt)

Not tech debt, but context for anyone reading this file wondering what's already
been addressed on the "site slow during registration rush" front: `ActivityViewSet`
structural caching, course-capacity race condition (`select_for_update`), N+1
fixes in absence creation/deletion and Bill total/payment cascades, and
rate-limited async PDF generation for bill confirmation emails. See CHANGELOG
4.5.0/4.5.1 entries and git log for detail if revisiting this area.
