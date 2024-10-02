from .handlers import get_step_handler
from .models import WizardStep


class WizardWorkflow:
    """Class to manage the dynamic registration process."""

    def __init__(self, user, registration_context):
        self.user = user
        self.registration_context = registration_context
        self.steps = WizardStep.objects.all().order_by("position")

    def get_visible_steps(self):
        """Return the list of visible steps based on the current registration context."""
        visible_steps = []
        for step in self.steps:
            handler = get_step_handler(step, self.registration_context)
            if handler.is_visible():
                visible_steps.append(step)
        return visible_steps

    def get_next_step(self, current_step):
        """Get the next step based on the current step's position."""
        visible_steps = self.get_visible_steps()
        for index, step in enumerate(visible_steps):
            if step == current_step and index + 1 < len(visible_steps):
                return visible_steps[index + 1]
        return None
