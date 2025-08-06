from django.conf import settings
from django.shortcuts import redirect


class StepHandler:
    """Base class for managing the visibility and completion status of a registration step."""

    def __init__(self, step, registration_context):
        """
        :param step: The `RegistrationStep` instance.
        :param registration_context: Context data for evaluating conditions (e.g., user input).
        """
        self.step = step
        self.registration_context = registration_context

    def is_visible(self):
        """Determine if the step is visible. Default is always visible."""
        return self.step.display_in_navigation

    def is_ready(self):
        return True

    def is_complete(self):
        """Determine if the step is complete. Override this method for step-specific logic."""
        return False


class EntryPointStepHandler(StepHandler):
    """
    Custom handler for the entry point that decides the next view.
    """

    def handle_step(self, request):
        """
        Custom logic to route the user based on their authentication status.
        """
        if request.user.is_authenticated:
            # Redirect to the next step for authenticated users
            return redirect("wizard:user-update")
        # Redirect to the form view for unauthenticated users
        return redirect("wizard:user-create")


class ProfileCreationStepHandler(StepHandler):
    """Handler for the profile creation step."""

    def is_visible(self):
        """The profile creation step is only visible for not registered users."""
        return not self.registration_context["user_registered"]

    def is_complete(self):
        """Check if the user has completed their profile."""
        return self.registration_context["user_registered"]


class ProfileUpdateStepHandler(StepHandler):
    """Handler for the profile update step."""

    def is_visible(self):
        """The profile update step is always visible."""
        return self.registration_context["user_registered"]

    def is_complete(self):
        """Check if the user has completed their profile."""
        return self.registration_context["user_registered"]

    def is_ready(self):
        return not self.registration_context.get("invoice")


class ChildInformationStepHandler(StepHandler):
    """Handler for child information step."""

    def is_ready(self):
        return self.registration_context["user_registered"] and not self.registration_context.get("invoice")

    def is_complete(self):
        """Complete if all required fields for children are filled."""
        return bool(self.registration_context["has_children"])


class ActivitiesStepHandler(StepHandler):
    """Handler for child information step."""

    def is_ready(self):
        return self.registration_context["has_children"] and not self.registration_context.get("invoice")

    def is_visible(self):
        """Visible if the user has children linked to their profile."""
        return True

    def is_complete(self):
        """Complete if all required fields for children are filled."""
        return bool(self.registration_context["registrations"])


class EquipmentPickupStepHandler(StepHandler):
    """Step handler for the equipment pickup step."""

    def is_visible(self):
        return settings.KEPCHUP_USE_APPOINTMENTS

    def is_ready(self):
        return self.registration_context["children_with_registrations"] and not self.registration_context.get(
            "invoice"
        )

    def is_complete(self):
        # Complete if a pickup appointment has been scheduled
        return (
            self.registration_context["invoice"]
            or self.registration_context.get("rentals")
            and all(rental.pickup_appointment for rental in self.registration_context.get("rentals"))
        )


class EquipmentReturnStepHandler(StepHandler):
    """Step handler for the equipment pickup step."""

    def is_visible(self):
        return settings.KEPCHUP_USE_APPOINTMENTS and self.registration_context.get("rentals")

    def is_ready(self):
        return self.registration_context.get("rentals") and not self.registration_context.get("invoice")

    def is_complete(self):
        # Complete if a pickup appointment has been scheduled
        return self.registration_context.get("rentals") and all(
            rental.return_appointment for rental in self.registration_context.get("rentals")
        )


class QuestionStepHandler(StepHandler):
    """Handler for question steps."""

    def __init__(self, step, registration_context):
        super().__init__(step, registration_context)
        self.questions = [
            question for question in registration_context["all_questions"] if question.step_id == step.id
        ]

    def is_visible(self):
        if not self.registration_context["registrations"]:
            return False
        return True  # any(question in self.registration_context["all_questions"] for question in self.questions)

    def is_ready(self):
        registrations = self.registration_context.get("registrations")
        invoice = self.registration_context.get("invoice")
        return registrations and not invoice

    def is_complete(self):
        return not any(question in self.registration_context["questions_not_answered"] for question in self.questions)


class PaymentStepHandler(StepHandler):
    def is_ready(self):
        return bool(self.registration_context.get("invoice"))


class ConfirmationStepHandler(StepHandler):
    def is_ready(self):
        if self.registration_context["questions_not_answered"]:
            return False
        if not self.registration_context.get("registrations") and not self.registration_context.get("rentals"):
            return False
        if self.registration_context.get("rentals"):
            return all(
                rental.return_appointment and rental.pickup_appointment
                for rental in self.registration_context.get("rentals")
            )

        return True

    def is_complete(self):
        return self.registration_context.get("validation") and self.registration_context["validation"].consent_given


class QuestionsEntryPointHandler(StepHandler):
    pass


class EquipmentEntryPointHandler(StepHandler):
    pass


def get_step_handler(step, registration_context):
    """Factory function to return the appropriate handler for a given step."""
    handler_mapping = {
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
    }
    handler_class = handler_mapping.get(step.slug, QuestionStepHandler)
    return handler_class(step, registration_context)
