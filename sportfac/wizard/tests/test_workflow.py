from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from sportfac.utils import TenantTestCase

from ..workflow import WizardWorkflow
from .factories import WizardStepFactory


class FakeHandler:
    """Stand-in for get_step_handler()'s real handlers - lets tests drive the
    workflow's own step-sequencing logic (get_next_step, get_visible_steps, ...)
    without depending on any specific StepHandler subclass's business rules, which are
    covered separately in test_handlers.py.
    """

    def __init__(self, step, registration_context):
        self.step = step

    def is_ready(self):
        return self.step.slug in READY_SLUGS

    def is_complete(self):
        return self.step.slug in COMPLETE_SLUGS

    def is_visible(self):
        return self.step.slug in VISIBLE_SLUGS


READY_SLUGS = set()
COMPLETE_SLUGS = set()
VISIBLE_SLUGS = set()


@patch("wizard.workflow.get_step_handler", new=lambda step, ctx: FakeHandler(step, ctx))
class WizardWorkflowTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        global READY_SLUGS, COMPLETE_SLUGS, VISIBLE_SLUGS
        READY_SLUGS, COMPLETE_SLUGS, VISIBLE_SLUGS = set(), set(), set()
        self.step_a = WizardStepFactory(slug="a", position=0)
        self.step_b = WizardStepFactory(slug="b", position=1)
        self.step_c = WizardStepFactory(slug="c", position=2)

    def test_get_all_steps_returns_every_step_regardless_of_visibility(self):
        VISIBLE_SLUGS.update({"a"})  # only "a" is visible
        workflow = WizardWorkflow(user=None, registration_context={})

        steps = workflow.get_all_steps()

        self.assertEqual([s.slug for s in steps], ["a", "b", "c"])

    def test_get_all_steps_flags_ready_and_complete_steps(self):
        READY_SLUGS.update({"a", "c"})
        COMPLETE_SLUGS.update({"a"})
        workflow = WizardWorkflow(user=None, registration_context={})

        steps = {s.slug: s for s in workflow.get_all_steps()}

        self.assertTrue(steps["a"].is_ready)
        self.assertTrue(steps["a"].is_complete)
        self.assertFalse(hasattr(steps["b"], "is_ready"))
        self.assertTrue(steps["c"].is_ready)
        self.assertFalse(hasattr(steps["c"], "is_complete"))

    def test_get_visible_steps_excludes_non_visible_ones_but_keeps_order(self):
        VISIBLE_SLUGS.update({"a", "c"})
        workflow = WizardWorkflow(user=None, registration_context={})

        steps = workflow.get_visible_steps()

        self.assertEqual([s.slug for s in steps], ["a", "c"])

    def test_get_visible_steps_also_flags_ready_and_complete_steps(self):
        READY_SLUGS.update({"a"})
        COMPLETE_SLUGS.update({"a"})
        VISIBLE_SLUGS.update({"a", "b", "c"})
        workflow = WizardWorkflow(user=None, registration_context={})

        steps = {s.slug: s for s in workflow.get_visible_steps()}

        self.assertTrue(steps["a"].is_ready)
        self.assertTrue(steps["a"].is_complete)
        self.assertFalse(hasattr(steps["b"], "is_ready"))

    def test_get_next_step_uses_every_step_not_only_visible_ones(self):
        # A step invisible right now can still become the "next step" target - e.g. it
        # becomes visible once the registrations for it exist - so get_next_step must
        # walk the full step list, unlike get_next_visible_step.
        VISIBLE_SLUGS.update({"a"})
        workflow = WizardWorkflow(user=None, registration_context={})

        next_step = workflow.get_next_step(self.step_a)

        self.assertEqual(next_step.slug, "b")

    def test_get_next_step_returns_none_for_the_last_step(self):
        workflow = WizardWorkflow(user=None, registration_context={})

        self.assertIsNone(workflow.get_next_step(self.step_c))

    def test_get_next_step_returns_none_for_a_step_not_in_the_list(self):
        unrelated_step = WizardStepFactory(slug="unrelated", position=99)
        workflow = WizardWorkflow(user=None, registration_context={})

        self.assertIsNone(workflow.get_next_step(unrelated_step))

    def test_get_next_visible_step_skips_hidden_steps(self):
        VISIBLE_SLUGS.update({"a", "c"})  # "b" is hidden
        workflow = WizardWorkflow(user=None, registration_context={})

        next_step = workflow.get_next_visible_step(self.step_a)

        self.assertEqual(next_step.slug, "c")

    def test_get_next_visible_step_returns_none_for_the_last_visible_step(self):
        VISIBLE_SLUGS.update({"a", "c"})
        workflow = WizardWorkflow(user=None, registration_context={})

        self.assertIsNone(workflow.get_next_visible_step(self.step_c))

    def test_get_previous_step_skips_hidden_steps(self):
        VISIBLE_SLUGS.update({"a", "c"})  # "b" is hidden
        workflow = WizardWorkflow(user=None, registration_context={})

        previous_step = workflow.get_previous_step(self.step_c)

        self.assertEqual(previous_step.slug, "a")

    def test_get_previous_step_returns_none_for_the_first_visible_step(self):
        VISIBLE_SLUGS.update({"a", "c"})
        workflow = WizardWorkflow(user=None, registration_context={})

        self.assertIsNone(workflow.get_previous_step(self.step_a))

    def test_steps_are_cached_across_workflow_instances(self):
        # WizardStep.objects.all() is only meant to be queried once per hour (per
        # tenant schema) - a second WizardWorkflow instance in the same request/process
        # must reuse the cached list, not re-hit the database.
        WizardWorkflow(user=None, registration_context={})  # primes the cache

        with CaptureQueriesContext(connection) as queries:
            WizardWorkflow(user=None, registration_context={})

        self.assertEqual(len(queries), 0)

    def test_cache_is_invalidated_when_a_step_is_added(self):
        # Regression test: WizardStep's post_save signal (clear_wizard_step_cache, in
        # models.py) used to delete a differently-named cache key ("all_wizard_steps",
        # no schema suffix) than the one WizardWorkflow actually reads/writes
        # ("all_wizard_steps_<schema>") - the signal never invalidated anything real, so
        # adding/editing/removing a step (or reordering, or toggling
        # display_in_navigation) kept serving the stale step list for up to an hour.
        WizardWorkflow(user=None, registration_context={})  # primes the cache

        WizardStepFactory(slug="d", position=3)

        workflow = WizardWorkflow(user=None, registration_context={})
        self.assertEqual([s.slug for s in workflow.get_all_steps()], ["a", "b", "c", "d"])
