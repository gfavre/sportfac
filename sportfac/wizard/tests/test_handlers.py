from types import SimpleNamespace
from unittest import TestCase

from django.test import override_settings

from ..handlers import ActivitiesStepHandler
from ..handlers import ChildInformationStepHandler
from ..handlers import ConfirmationStepHandler
from ..handlers import EntryPointStepHandler
from ..handlers import EquipmentEntryPointHandler
from ..handlers import EquipmentPickupStepHandler
from ..handlers import EquipmentReturnStepHandler
from ..handlers import PaymentStepHandler
from ..handlers import ProfileCreationStepHandler
from ..handlers import ProfileUpdateStepHandler
from ..handlers import QuestionsEntryPointHandler
from ..handlers import QuestionStepHandler
from ..handlers import StepHandler
from ..handlers import SuccessStepHandler
from ..handlers import get_step_handler


def make_step(slug="step", display_in_navigation=True, step_id=1):
    return SimpleNamespace(slug=slug, display_in_navigation=display_in_navigation, id=step_id)


class FakeQuestion:
    # A plain class, not SimpleNamespace: SimpleNamespace defines __eq__ (by-value
    # comparison), which makes Python drop its default __hash__ - these need to go into
    # a set() the same way real ExtraNeed model instances do.
    def __init__(self, step_id):
        self.step_id = step_id


def make_context(**overrides):
    context = {
        "user_registered": True,
        "has_children": True,
        "children_with_registrations": True,
        "registrations": ["registration"],
        "all_questions": set(),
        "questions_not_answered": set(),
        "invoice": None,
        "blocking_payment": False,
        "rentals": [],
        "validation": None,
    }
    context.update(overrides)
    return context


class StepHandlerBaseTests(TestCase):
    def test_is_visible_follows_display_in_navigation(self):
        self.assertTrue(StepHandler(make_step(display_in_navigation=True), make_context()).is_visible())
        self.assertFalse(StepHandler(make_step(display_in_navigation=False), make_context()).is_visible())

    def test_is_ready_defaults_to_true(self):
        self.assertTrue(StepHandler(make_step(), make_context()).is_ready())

    def test_is_complete_defaults_to_false(self):
        self.assertFalse(StepHandler(make_step(), make_context()).is_complete())


class ProfileCreationStepHandlerTests(TestCase):
    def test_visible_and_incomplete_when_user_not_registered(self):
        handler = ProfileCreationStepHandler(make_step(), make_context(user_registered=False))
        self.assertTrue(handler.is_visible())
        self.assertFalse(handler.is_complete())

    def test_hidden_and_complete_once_registered(self):
        handler = ProfileCreationStepHandler(make_step(), make_context(user_registered=True))
        self.assertFalse(handler.is_visible())
        self.assertTrue(handler.is_complete())


class ProfileUpdateStepHandlerTests(TestCase):
    def test_blocked_while_payment_is_blocking(self):
        handler = ProfileUpdateStepHandler(make_step(), make_context(blocking_payment=True))
        self.assertFalse(handler.is_ready())

    def test_ready_when_not_blocked(self):
        handler = ProfileUpdateStepHandler(make_step(), make_context(blocking_payment=False))
        self.assertTrue(handler.is_ready())

    def test_visible_and_complete_only_once_registered(self):
        handler = ProfileUpdateStepHandler(make_step(), make_context(user_registered=True))
        self.assertTrue(handler.is_visible())
        self.assertTrue(handler.is_complete())

        handler = ProfileUpdateStepHandler(make_step(), make_context(user_registered=False))
        self.assertFalse(handler.is_visible())
        self.assertFalse(handler.is_complete())


class ChildInformationStepHandlerTests(TestCase):
    def test_not_ready_if_user_not_registered(self):
        handler = ChildInformationStepHandler(make_step(), make_context(user_registered=False))
        self.assertFalse(handler.is_ready())

    def test_blocked_by_pending_payment_even_if_registered(self):
        handler = ChildInformationStepHandler(make_step(), make_context(user_registered=True, blocking_payment=True))
        self.assertFalse(handler.is_ready())

    def test_ready_when_registered_and_not_blocked(self):
        handler = ChildInformationStepHandler(make_step(), make_context(user_registered=True, blocking_payment=False))
        self.assertTrue(handler.is_ready())

    def test_complete_only_if_has_children(self):
        self.assertTrue(ChildInformationStepHandler(make_step(), make_context(has_children=True)).is_complete())
        self.assertFalse(ChildInformationStepHandler(make_step(), make_context(has_children=False)).is_complete())


class ActivitiesStepHandlerTests(TestCase):
    def test_not_ready_without_children(self):
        handler = ActivitiesStepHandler(make_step(), make_context(has_children=False))
        self.assertFalse(handler.is_ready())

    def test_blocked_by_pending_payment(self):
        handler = ActivitiesStepHandler(make_step(), make_context(has_children=True, blocking_payment=True))
        self.assertFalse(handler.is_ready())

    def test_ready_with_children_and_no_blocking_payment(self):
        handler = ActivitiesStepHandler(make_step(), make_context(has_children=True, blocking_payment=False))
        self.assertTrue(handler.is_ready())

    def test_always_visible(self):
        # Unlike is_ready, is_visible does not depend on has_children - a family with
        # no children yet must still see the "Activities" entry in the navigation.
        handler = ActivitiesStepHandler(make_step(), make_context(has_children=False))
        self.assertTrue(handler.is_visible())

    def test_complete_only_with_registrations(self):
        self.assertTrue(ActivitiesStepHandler(make_step(), make_context(registrations=["r"])).is_complete())
        self.assertFalse(ActivitiesStepHandler(make_step(), make_context(registrations=[])).is_complete())


class EquipmentPickupStepHandlerTests(TestCase):
    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    def test_visible_when_appointments_enabled(self):
        handler = EquipmentPickupStepHandler(make_step(), make_context())
        self.assertTrue(handler.is_visible())

    @override_settings(KEPCHUP_USE_APPOINTMENTS=False)
    def test_hidden_when_appointments_disabled(self):
        handler = EquipmentPickupStepHandler(make_step(), make_context())
        self.assertFalse(handler.is_visible())

    def test_not_ready_without_children_with_registrations(self):
        handler = EquipmentPickupStepHandler(make_step(), make_context(children_with_registrations=False))
        self.assertFalse(handler.is_ready())

    def test_blocked_by_pending_payment(self):
        handler = EquipmentPickupStepHandler(
            make_step(), make_context(children_with_registrations=True, blocking_payment=True)
        )
        self.assertFalse(handler.is_ready())

    def test_complete_if_invoice_present(self):
        handler = EquipmentPickupStepHandler(make_step(), make_context(invoice="an invoice"))
        self.assertTrue(handler.is_complete())

    def test_complete_if_every_rental_has_a_pickup_appointment(self):
        rentals = [SimpleNamespace(pickup_appointment=True), SimpleNamespace(pickup_appointment=True)]
        handler = EquipmentPickupStepHandler(make_step(), make_context(invoice=None, rentals=rentals))
        self.assertTrue(handler.is_complete())

    def test_incomplete_if_any_rental_missing_a_pickup_appointment(self):
        rentals = [SimpleNamespace(pickup_appointment=True), SimpleNamespace(pickup_appointment=False)]
        handler = EquipmentPickupStepHandler(make_step(), make_context(invoice=None, rentals=rentals))
        self.assertFalse(handler.is_complete())

    def test_incomplete_with_no_invoice_and_no_rentals(self):
        handler = EquipmentPickupStepHandler(make_step(), make_context(invoice=None, rentals=[]))
        self.assertFalse(handler.is_complete())


class EquipmentReturnStepHandlerTests(TestCase):
    @override_settings(KEPCHUP_USE_APPOINTMENTS=True)
    def test_visible_only_with_rentals(self):
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=["rental"]))
        self.assertTrue(handler.is_visible())
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=[]))
        self.assertFalse(handler.is_visible())

    @override_settings(KEPCHUP_USE_APPOINTMENTS=False)
    def test_hidden_when_appointments_disabled_even_with_rentals(self):
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=["rental"]))
        self.assertFalse(handler.is_visible())

    def test_not_ready_without_rentals(self):
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=[]))
        self.assertFalse(handler.is_ready())

    def test_blocked_by_pending_payment(self):
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=["rental"], blocking_payment=True))
        self.assertFalse(handler.is_ready())

    def test_complete_if_every_rental_has_a_return_appointment(self):
        rentals = [SimpleNamespace(return_appointment=True), SimpleNamespace(return_appointment=True)]
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=rentals))
        self.assertTrue(handler.is_complete())

    def test_incomplete_if_any_rental_missing_a_return_appointment(self):
        rentals = [SimpleNamespace(return_appointment=True), SimpleNamespace(return_appointment=False)]
        handler = EquipmentReturnStepHandler(make_step(), make_context(rentals=rentals))
        self.assertFalse(handler.is_complete())


class QuestionStepHandlerTests(TestCase):
    def test_only_keeps_questions_belonging_to_its_own_step(self):
        q1 = FakeQuestion(1)
        q2 = FakeQuestion(2)
        handler = QuestionStepHandler(make_step(step_id=1), make_context(all_questions={q1, q2}))
        self.assertEqual(handler.questions, [q1])

    def test_not_visible_without_registrations(self):
        q1 = FakeQuestion(1)
        handler = QuestionStepHandler(make_step(step_id=1), make_context(registrations=[], all_questions={q1}))
        self.assertFalse(handler.is_visible())

    def test_visible_only_if_one_of_its_questions_is_in_all_questions(self):
        q1 = FakeQuestion(1)
        other_step_question = FakeQuestion(2)
        handler = QuestionStepHandler(
            make_step(step_id=1), make_context(registrations=["r"], all_questions={other_step_question})
        )
        self.assertFalse(handler.is_visible())

        handler = QuestionStepHandler(make_step(step_id=1), make_context(registrations=["r"], all_questions={q1}))
        self.assertTrue(handler.is_visible())

    def test_not_ready_without_registrations(self):
        handler = QuestionStepHandler(make_step(step_id=1), make_context(registrations=[]))
        self.assertFalse(handler.is_ready())

    def test_blocked_by_pending_payment(self):
        handler = QuestionStepHandler(make_step(step_id=1), make_context(registrations=["r"], blocking_payment=True))
        self.assertFalse(handler.is_ready())

    def test_complete_when_none_of_its_questions_are_unanswered(self):
        q1 = FakeQuestion(1)
        handler = QuestionStepHandler(
            make_step(step_id=1), make_context(all_questions={q1}, questions_not_answered=set())
        )
        self.assertTrue(handler.is_complete())

    def test_incomplete_if_one_of_its_questions_is_unanswered(self):
        q1 = FakeQuestion(1)
        handler = QuestionStepHandler(
            make_step(step_id=1), make_context(all_questions={q1}, questions_not_answered={q1})
        )
        self.assertFalse(handler.is_complete())


class PaymentStepHandlerTests(TestCase):
    def test_ready_only_with_an_invoice(self):
        self.assertTrue(PaymentStepHandler(make_step(), make_context(invoice="invoice")).is_ready())
        self.assertFalse(PaymentStepHandler(make_step(), make_context(invoice=None)).is_ready())

    def test_complete_only_if_invoice_is_paid(self):
        paid_invoice = SimpleNamespace(is_paid=True)
        unpaid_invoice = SimpleNamespace(is_paid=False)
        self.assertTrue(PaymentStepHandler(make_step(), make_context(invoice=paid_invoice)).is_complete())
        self.assertFalse(PaymentStepHandler(make_step(), make_context(invoice=unpaid_invoice)).is_complete())
        self.assertFalse(PaymentStepHandler(make_step(), make_context(invoice=None)).is_complete())


class SuccessStepHandlerTests(TestCase):
    def test_always_ready(self):
        self.assertTrue(SuccessStepHandler(make_step(), make_context()).is_ready())


class ConfirmationStepHandlerTests(TestCase):
    def test_not_ready_with_unanswered_questions(self):
        handler = ConfirmationStepHandler(make_step(), make_context(questions_not_answered={"q"}))
        self.assertFalse(handler.is_ready())

    def test_not_ready_without_registrations(self):
        handler = ConfirmationStepHandler(make_step(), make_context(registrations=[]))
        self.assertFalse(handler.is_ready())

    def test_not_ready_if_a_rental_is_missing_an_appointment(self):
        rentals = [SimpleNamespace(pickup_appointment=True, return_appointment=False)]
        handler = ConfirmationStepHandler(make_step(), make_context(rentals=rentals))
        self.assertFalse(handler.is_ready())

    def test_ready_if_every_rental_has_both_appointments(self):
        rentals = [SimpleNamespace(pickup_appointment=True, return_appointment=True)]
        handler = ConfirmationStepHandler(make_step(), make_context(rentals=rentals))
        self.assertTrue(handler.is_ready())

    def test_ready_without_rentals_at_all(self):
        handler = ConfirmationStepHandler(make_step(), make_context(rentals=[]))
        self.assertTrue(handler.is_ready())

    def test_complete_only_if_consent_given(self):
        given = SimpleNamespace(consent_given=True)
        not_given = SimpleNamespace(consent_given=False)
        self.assertTrue(ConfirmationStepHandler(make_step(), make_context(validation=given)).is_complete())
        self.assertFalse(ConfirmationStepHandler(make_step(), make_context(validation=not_given)).is_complete())
        self.assertFalse(ConfirmationStepHandler(make_step(), make_context(validation=None)).is_complete())


class GetStepHandlerTests(TestCase):
    def test_maps_known_slugs_to_their_dedicated_handler_class(self):
        cases = {
            "entry_point": EntryPointStepHandler,
            "user-create": ProfileCreationStepHandler,
            "user-update": ProfileUpdateStepHandler,
            "children": ChildInformationStepHandler,
            "activities": ActivitiesStepHandler,
            "questions": QuestionsEntryPointHandler,
            "equipment": EquipmentPickupStepHandler,
            "equipment-return": EquipmentReturnStepHandler,
            "equipment-need-return": EquipmentEntryPointHandler,
            "confirmation": ConfirmationStepHandler,
            "payment": PaymentStepHandler,
            "payment-failure": PaymentStepHandler,
            "payment-success": PaymentStepHandler,
            "success": SuccessStepHandler,
        }
        for slug, expected_class in cases.items():
            handler = get_step_handler(make_step(slug=slug, step_id=1), make_context(all_questions=set()))
            self.assertIsInstance(handler, expected_class, slug)

    def test_unknown_slug_falls_back_to_question_step_handler(self):
        # This is how per-tenant custom question steps (arbitrary slugs configured in the
        # backend) are actually handled - anything not in the explicit mapping is assumed
        # to be a question step.
        handler = get_step_handler(make_step(slug="some-custom-question-step", step_id=1), make_context())
        self.assertIsInstance(handler, QuestionStepHandler)
