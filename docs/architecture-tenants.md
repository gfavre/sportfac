# Tenants, periods, and deployments

Written 2026-08-23 while investigating the stale-session incident (see
`docs/reports/2026-08-23-stale-tenant-session-incident.md`). Reflects what was
confirmed by reading the code, not assumption — update it if it drifts from
reality.

## One deployment per school/city, not per tenant

Each school or city (Coppet, Oron, Montreux, ...) runs its **own separate
deployment**: own database, own Redis instance, own `sportfac/settings/<name>.py`
settings module, own theme (`sportfac/themes/<name>/`). There is no
infrastructure shared between schools — a session, a cache entry, or a DB row
in one deployment can never be seen by another. This matters because it's easy
to misread `django-tenants` multi-tenancy (see below) as "one deployment
serving many schools" — it isn't; it's "one deployment, multiple *periods*, for
one school".

## Tenants = school-year periods, within one deployment

`django-tenants` (schema-per-tenant Postgres) is used *within* a single
school's deployment to represent different **school-year periods**
(`backend.models.YearTenant`), e.g. "2025-2026" and "2026-2027" as separate
Postgres schemas in the same database. Switching or previewing a "tenant" in
this codebase means switching which period's data you're looking at — never a
different school.

- `backend.models.Domain` (one per `YearTenant`, via `.domains`) carries the
  `is_current` boolean: exactly one `Domain` across the whole deployment is
  the *production* one at any given time — the period ordinary visitors land
  on.
- `YearTenant.is_production` is just `self.domains.first().is_current`.

## Which period a request resolves to

Despite the name, tenant resolution here is **not** based on the actual HTTP
hostname (`django-tenants`' usual model). `sportfac.middleware.VersionMiddleware`
overrides `hostname_from_request` to resolve from `request.session["period"]`
(`settings.VERSION_SESSION_NAME`) instead, defaulting to whichever `Domain` is
currently `is_current` if the session has no pin. As of 4.6.5, only
`kepchup_staff` (`FamilyUser.is_kepchup_staff` — manager, restricted manager,
superuser, or instructor) may keep a session pinned to a non-production period
(deliberate preview, `backend.views.year_views.ChangeYearFormView`); everyone
else always resolves to the live production period, self-healing any stale pin
on every request.

## Auth and sessions are shared across periods, not per-period

`AUTH_USER_MODEL` (`profiles.FamilyUser`) and Django's session store both live
in the **shared/public** schema, not inside a period's own schema — `profiles`
is a `SHARED_APPS` entry, not a `TENANT_APPS` one. Consequence: one family
account, and one login session, persists across a production period switch;
switching production doesn't log anyone out or invalidate anything by itself
(that's what `log_everyone_out` is *supposed* to do — see the incident report
for how it silently didn't, in production, until 4.6.5).

This also means a "log everyone out" action is scoped to **one school's whole
deployment** (every period within it shares the same session store), never
crosses into another school (fully separate infra, see above) — but it isn't
scoped to a single period either, since sessions aren't period-scoped.

## The red "not production" banner

`not_production.css` (loaded whenever `not request.tenant.is_production` in
`base.html`/the theme `base.html` files) is what renders the red banner.
It's purely CSS keyed off which period the request resolved to — nothing
about it is inherently staff-only, it's just that only staff are supposed to
ever have a session pinned somewhere other than production. See the incident
report for the case where that assumption didn't hold.

## Themes

`sportfac/themes/<name>/templates/` holds each school's full override of the
base templates (colors, logo, extra branding). These are **complete copies**
of `sportfac/templates/*.html`, not `{% extends %}`-based overrides of a
shared base — see `TECH_DEBT.md` for the maintenance cost this has already
caused (a fix landed in the default `base.html` silently not reaching most
themes).
