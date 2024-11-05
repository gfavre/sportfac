from django.core.cache import cache

from .handlers import get_step_handler
from .models import WizardStep


class WizardWorkflow:
    """Class to manage the dynamic registration process."""

    def __init__(self, user, registration_context):
        self.user = user
        self.registration_context = registration_context
        wizard_steps = cache.get("all_wizard_steps")
        if wizard_steps is None:
            # Cache miss, so we query the database
            wizard_steps = list(WizardStep.objects.all())
            cache.set("all_wizard_steps", wizard_steps, None)
        self.steps = wizard_steps

    def get_visible_steps(self):
        """Return the list of visible steps based on the current registration context."""
        visible_steps = []
        for step in self.steps:
            handler = get_step_handler(step, self.registration_context)
            if handler.is_ready():
                step.is_ready = True
            if handler.is_complete():
                step.is_complete = True
            if handler.is_visible():
                visible_steps.append(step)
        return visible_steps

    def get_all_steps(self):
        """Return the list of all steps that are ready."""
        for step in self.steps:
            handler = get_step_handler(step, self.registration_context)
            if handler.is_ready():
                step.is_ready = True
            if handler.is_complete():
                step.is_complete = True
        return self.steps

    def get_next_step(self, current_step):
        """Get the next step based on the current step's position."""
        # All steps, because this one might change the visibility of the next step
        steps = self.get_all_steps()
        for index, step in enumerate(steps):
            if step == current_step and index + 1 < len(steps):
                return steps[index + 1]
        return None

    def get_next_visible_step(self, current_step):
        """Get the next step based on the current step's position."""
        # All visible steps, because nothing could have changed that revokes a previous step
        steps = self.get_visible_steps()
        for index, step in enumerate(steps):
            if step == current_step and index + 1 < len(steps):
                return steps[index + 1]
        return None

    def get_previous_step(self, current_step):
        """Get the next step based on the current step's position."""
        # All visible steps, because nothing could have changed that revokes a previous step
        steps = self.get_visible_steps()
        for index, step in enumerate(steps):
            if step == current_step and index - 1 >= 0:
                return steps[index - 1]
        return None
