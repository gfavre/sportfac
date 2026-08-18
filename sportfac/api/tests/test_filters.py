from django.urls import reverse

from activities.tests.factories import CourseFactory
from profiles.tests.factories import FamilyUserFactory
from registrations.models import Registration
from registrations.tests.factories import ChildFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from ..filters import cleanup_value
from .utils import UserMixin


def datatables_columns_params(columns):
    """Build the columns[i][...] query params DataTables sends for a real
    (non-ad-hoc) request - a minimal test request that skips these never
    triggers DatatablesRenderer's field-pruning, silently hiding bugs that
    only show up against a real browser request."""
    params = {}
    for i, (data, name) in enumerate(columns):
        params[f"columns[{i}][data]"] = data
        params[f"columns[{i}][name]"] = name or ""
        params[f"columns[{i}][searchable]"] = "false" if not name else "true"
        params[f"columns[{i}][orderable]"] = "false" if not name else "true"
    return params


class CleanupValueChoicesFieldTests(TenantTestCase):
    """Regression tests for the searchPanes fix on 2026-08-18: DataTables SearchPanes
    (dt-1.10.24/sp-1.2.1) sends back the raw choice key it was given as an option's
    "value" (e.g. "canceled"), not its label ("Annulée") - the opposite of what the
    code previously assumed, so every choice-field pane filter silently matched
    nothing. Found via a real captured browser request, not by guessing."""

    def test_raw_choice_value_resolves_to_itself(self):
        accessor, values = cleanup_value(Registration, "status", ["canceled"])
        self.assertEqual(accessor, "status__in")
        self.assertEqual(values, ["canceled"])

    def test_label_still_resolves_for_backward_compatibility(self):
        label = dict(Registration.STATUS)["canceled"]
        accessor, values = cleanup_value(Registration, "status", [label])
        self.assertEqual(accessor, "status__in")
        self.assertEqual(values, ["canceled"])

    def test_unknown_value_resolves_to_none(self):
        accessor, values = cleanup_value(Registration, "status", ["not-a-real-status"])
        self.assertEqual(values, [None])


class RegistrationsSearchPanesIntegrationTest(UserMixin, TenantTestCase):
    """Same bug, exercised through the actual endpoint with the literal query string
    captured from a real browser click on the "Annulée" search pane."""

    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        course = CourseFactory()
        for status in ("canceled",) * 3 + ("valid",) * 5 + ("waiting",) * 2:
            child = ChildFactory(family=FamilyUserFactory())
            RegistrationFactory(child=child, course=course, status=status)

    REGISTRATIONS_COLUMNS = [
        ("course", "course.number"),
        ("activity", "course.activity.name"),
        ("day_name", "course.day"),
        ("start_date", "course.start_date"),
        ("start_time", "course.start_time"),
        ("bib_number", "child.bib_number"),
        ("child", "child.first_name,child.last_name"),
        ("status_display", "status"),
        ("actions", None),
    ]

    def test_clicking_canceled_pane_filters_to_canceled_registrations_only(self):
        self.login(self.manager)
        params = {
            "draw": 1,
            "start": 0,
            "length": 50,
            **datatables_columns_params(self.REGISTRATIONS_COLUMNS),
        }
        params["searchPanes[status_display][0]"] = ["canceled"]

        response = self.tenant_client.get(reverse("api:all_registrations"), params, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recordsFiltered"], 3)
        self.assertTrue(all(row["is_canceled"] for row in data["data"]))

    def test_status_cell_fields_survive_field_pruning(self):
        """Regression test for a bug found alongside the one above:
        DatatablesRenderer strips any serializer field that isn't one of the
        request's declared columns[i][data] - is_canceled/cancelation_date/etc.
        ride inside the status_display cell's render() rather than being their
        own column, so a real request (which always declares columns[]) would
        silently lose them without datatables_always_serialize on the
        serializer's Meta."""
        self.login(self.manager)
        params = {
            "draw": 1,
            "start": 0,
            "length": 50,
            **datatables_columns_params(self.REGISTRATIONS_COLUMNS),
        }
        response = self.tenant_client.get(reverse("api:all_registrations"), params, HTTP_ACCEPT="application/json")
        row = response.json()["data"][0]
        for field in (
            "is_canceled",
            "cancelation_date",
            "cancelation_reason_display",
            "cancelation_person_name",
            "confirmation_sent_on",
        ):
            self.assertIn(field, row, f"{field!r} was pruned from a real request's response")


class ChildrenDatatableIntegrationTest(UserMixin, TenantTestCase):
    """DashboardChildrenView/ChildDatatableSerializer bugs, all only reproducible
    against a real, full columns[] request - see datatables_columns_params()."""

    CHILDREN_COLUMNS = [
        ("full_name", "first_name,last_name"),
        ("family", "family.last_name,family.first_name"),
        ("school_year", "school_year.year"),
        ("is_blacklisted", "is_blacklisted"),
        ("actions", None),
    ]

    def _request(self, **extra_params):
        manager = FamilyUserFactory(is_manager=True)
        self.login(manager)
        params = {
            "draw": 1,
            "start": 0,
            "length": 50,
            **datatables_columns_params(self.CHILDREN_COLUMNS),
            **extra_params,
        }
        return self.tenant_client.get(reverse("api:all_children"), params, HTTP_ACCEPT="application/json")

    def test_url_and_school_name_survive_field_pruning(self):
        ChildFactory(family=FamilyUserFactory())
        response = self._request()
        row = response.json()["data"][0]
        for field in ("url", "school_name", "is_blacklisted"):
            self.assertIn(field, row, f"{field!r} was pruned from a real request's response")

    def test_global_search_by_name(self):
        """Regression test for the 2026-08-18 bug: the school_year column's
        DataTables `name` pointed straight at the school_year FK
        (`{name: 'school_year'}`) - the global search box applies `icontains`
        across every searchable column's name at once (not just the one being
        typed into), and `icontains` directly on a bare ForeignKey raises
        FieldError, so *any* text typed in the search box 500'd the whole
        request regardless of which column the user actually meant to search -
        matching the reported "search by name doesn't work". Fixed by pointing
        the column at `school_year.year` (a real field) instead."""
        ChildFactory(family=FamilyUserFactory(), first_name="Zbigniew", last_name="Kowalski")
        ChildFactory(family=FamilyUserFactory(), first_name="Alice", last_name="Martin")

        response = self._request(**{"search[value]": "Kowalski", "search[regex]": "false"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recordsFiltered"], 1)
        self.assertEqual(data["data"][0]["full_name"], "Zbigniew Kowalski")
