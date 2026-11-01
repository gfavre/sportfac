# Superadministrator health dashboard

`/health` (or `/hiver/health` on Montreux winter) is restricted to active
superusers. The account menu links to it below Django admin in all navbar
variants. The existing `/backend/health/` route uses the same dashboard.
Responses are not cached. Refreshing reruns the checks.

The dashboard includes the existing database, cache, Redis broker/queue,
disk, memory and CPU checks, plus secondary database and cache aliases.
Cache checks use temporary keys; no business data is modified.

External checks are separate from the public `/_health-kc/` probe:

- PostFinance: authenticated transaction count, including on an empty space.
  No payment is created, confirmed or updated.
- Datatrans: authenticated status read for an existing transaction in the
  request's current period. An empty period produces a warning, not success.
- Postmark: authenticated `GET /server`, without displaying the returned
  tokens or other account information. SMTP backends open/close a connection
  without sending a message; other email backends report the lack of a check.
- SSO, PhantomJsCloud and reCAPTCHA: HTTPS availability only. The warning
  explicitly says that credentials and complete workflows were not verified.
- Sentry: TLS connectivity to the DSN host only; no event is sent.

External requests have a three-second connection/read timeout. Provider
responses and exception strings are never displayed or logged by these checks.
Disabled integrations are distinguished from failures. A successful read API
does not prove that payment capture, mail delivery, callbacks or PDF rendering
will succeed. Celery broker connectivity/queue size does not prove worker health.

Like every authenticated, tenant-aware application page, this dashboard depends
on middleware and authentication working first. A complete database or session
Redis outage may prevent access to it; use external monitoring/server-side
diagnostics for that situation.

API references: [Postmark server API](https://postmarkapp.com/developer/api/server-api),
[PostFinance SDK](https://github.com/pfpayments/python-sdk),
[Datatrans transaction status](https://api-reference.datatrans.ch/),
[PhantomJsCloud HTTP API](https://phantomjscloud.com/docs/http-api/).
