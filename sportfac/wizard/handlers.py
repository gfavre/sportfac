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
        """The profile creation step is always visible."""
        return True

    def is_complete(self):
        """Check if the user has completed their profile."""
        return bool(self.registration_context.get("profile_complete", False))


class ProfileUpdateStepHandler(StepHandler):
    """Handler for the profile update step."""

    def is_visible(self):
        """The profile update step is always visible."""
        return True

    def is_complete(self):
        """Check if the user has completed their profile."""
        return bool(self.registration_context.get("profile_complete", False))


class ChildInformationStepHandler(StepHandler):
    """Handler for child information step."""

    def is_visible(self):
        """Visible if the user has children linked to their profile."""
        return bool(self.registration_context.get("has_children", False))

    def is_complete(self):
        """Complete if all required fields for children are filled."""
        return self.registration_context.get("child_info_complete", False)


class MaterialPickupStepHandler(StepHandler):
    """Step handler for the material pickup step."""

    def is_visible(self):
        # Only show this step if the user has selected an activity that requires material pickup
        selected_activities = self.registration_context.get("selected_activities", [])
        return any(activity.requires_material for activity in selected_activities)

    def is_complete(self):
        # Complete if a pickup appointment has been scheduled
        return bool(self.registration_context.get("pickup_appointment"))


def get_step_handler(step, registration_context):
    """Factory function to return the appropriate handler for a given step."""
    handler_mapping = {
        "entry_point": EntryPointStepHandler,
        "user-create": ProfileCreationStepHandler,
        "user-update": ProfileUpdateStepHandler,
        "child_information": ChildInformationStepHandler,
        # Add more mappings here for different steps
    }
    handler_class = handler_mapping.get(step.slug, StepHandler)
    return handler_class(step, registration_context)