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
        return True

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
        return not self.registration_context["user"].is_authenticated

    def is_complete(self):
        """Check if the user has completed their profile."""
        return bool(self.registration_context["user"].is_authenticated)


class ProfileUpdateStepHandler(StepHandler):
    """Handler for the profile update step."""

    def is_visible(self):
        """The profile update step is always visible."""
        return self.registration_context["user"].is_authenticated

    def is_complete(self):
        """Check if the user has completed their profile."""
        return bool(self.registration_context["user"].is_authenticated)


class ChildInformationStepHandler(StepHandler):
    """Handler for child information step."""

    def is_ready(self):
        return self.registration_context.get("user").is_authenticated

    def is_visible(self):
        """Visible if the user has children linked to their profile."""
        return True

    def is_complete(self):
        """Complete if all required fields for children are filled."""
        return bool(self.registration_context["has_children"])


class ActivitiesStepHandler(StepHandler):
    """Handler for child information step."""

    def is_ready(self):
        user = self.registration_context.get("user")
        return user.is_authenticated and user.children.exists() and not self.registration_context.get("invoice")

    def is_visible(self):
        """Visible if the user has children linked to their profile."""
        return True

    def is_complete(self):
        """Complete if all required fields for children are filled."""
        return self.registration_context.get("has_registrations", False)


class EquipmentPickupStepHandler(StepHandler):
    """Step handler for the equipment pickup step."""

    def is_visible(self):
        return settings.KEPCHUP_USE_APPOINTMENTS

    def is_ready(self):
        user = self.registration_context.get("user")
        return user.is_authenticated and user.children.exists() and not self.registration_context.get("invoice")

    def is_complete(self):
        # Complete if a pickup appointment has been scheduled
        return bool(self.registration_context.get("pickup_appointment"))


class EquipmentReturnStepHandler(StepHandler):
    """Step handler for the equipment pickup step."""

    def is_visible(self):
        return settings.KEPCHUP_USE_APPOINTMENTS

    def is_ready(self):
        user = self.registration_context.get("user")
        rentals = self.registration_context.get("rentals")
        if not user.is_authenticated and user.children.exists():
            return False
        return not self.registration_context.get("invoice") and bool(rentals)

    def is_complete(self):
        # Complete if a pickup appointment has been scheduled
        return bool(self.registration_context.get("pickup_appointment"))


class QuestionStepHandler(StepHandler):
    """Handler for question steps."""

    def is_visible(self):
        if not self.registration_context["registrations"]:
            return False
        for question in self.step.questions.prefetch_related("courses"):
            if self.registration_context["registrations"].filter(course__in=question.courses.all()).exists():
                return True
        return False

    def is_ready(self):
        return not bool(self.registration_context.get("invoice"))

    def is_complete(self):
        return True


class PaymentStepHandler(StepHandler):
    def is_ready(self):
        return bool(self.registration_context.get("invoice"))


class ConfirmationStepHandler(StepHandler):
    def is_ready(self):
        return not self.registration_context.get("invoice") and self.registration_context.get("registrations")


def get_step_handler(step, registration_context):
    """Factory function to return the appropriate handler for a given step."""
    handler_mapping = {
        "entry_point": EntryPointStepHandler,
        "user-create": ProfileCreationStepHandler,
        "user-update": ProfileUpdateStepHandler,
        "children": ChildInformationStepHandler,
        "activities": ActivitiesStepHandler,
        "equipment": EquipmentPickupStepHandler,
        "equipment-return": EquipmentReturnStepHandler,
        "payment": PaymentStepHandler,
        "confirmation": ConfirmationStepHandler,
        # Add more mappings here for different steps
    }
    handler_class = handler_mapping.get(step.slug, QuestionStepHandler)
    return handler_class(step, registration_context)
