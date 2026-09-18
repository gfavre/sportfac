# Backend table navigation

The opt-in helper `backend/static/backend/js/datatable-url-state.js` persists
DataTables state in the current URL using `history.replaceState`. It supports
client-side and server-side tables, pagination, page size, column radio filters,
external form controls and SearchPanes. It does not store state in localStorage
or sessionStorage. Row selections for bulk actions are deliberately not saved.

To enable another list:

1. Give its table a unique ID and load the standalone static script before the
   initialization code. Keep the cache version in sync with other references.
2. Replace `$('#table').DataTable(options)` with
   `window.dataTableUrlState('#table', options, filters)`.
3. Optional `filters` entries have `param`, `selector`, `defaultValue` and
   either a `values` map or a `validate(value)` function. A radio filter with
   `column` uses the mapped value as that column's search term; external
   controls without `column` are restored and saved, with the actual filtering
   left to the page's predicate. See the course and invoice lists.
4. Add the list URL name to `LIST_RETURN_NAMES` in `backend/views/mixins.py`.
   Add any extra filter keys to `LIST_STATE_PARAMETERS`.
5. Add `ListReturnMixin` before the existing bases of the relevant detail/edit
   views. Overrides of `get_success_url()` must check `get_list_return_url()`
   before applying their existing fallback. Use `list_return_url` for explicit
   cancel links when available.

Links in the table carry `list_return` to the destination. The mixin accepts only
relative URLs pointing to one of the listed backend routes, and keeps only the
known query parameters. `backend/base.html` embeds the validated return URL and loads
`list-return.js`, which propagates that validated URL through detail/edit links
and explicit form actions. Normal navigation without `list_return` retains the
existing redirect behavior.

URL parameters are `q`, `order` (JSON column/direction pairs), one-based `page`,
`length`, and `panes` (only selections/search/order, not the entire pane dataset).
Invoices also use `date_from`, `date_to`, `status`, `amount`; courses use `only_js`.
The invoice date names intentionally differ from the older server-side
`start`/`end` parameters: filtering the loaded table must still allow widening
or clearing a range after returning from an edit.

The helper seeds restored SearchPanes values into the **first Ajax request**:
SearchPanes 1.2 otherwise restores the controls after fetching unfiltered rows.
The templates use 1.2.2: 1.2.1 cannot reliably restore this compact state. Tests
read the version and registration status-pane configuration from the template.
Use `searchPanes.show: true` for essential filters such as registration status,
so the automatic uniqueness threshold cannot hide them on small result sets.
It also disables browser storage on the internal pane tables, not just the main
table. Preserve these behaviors when upgrading DataTables/SearchPanes.

These scripts are standalone Django static assets, not part of the legacy
AngularJS bundles. Deploy them through the normal `collectstatic` workflow.
JavaScript test instructions are in `tests/js/README.md`; Django return-navigation
regressions are in `backend/tests/test_views/test_list_return.py`.
