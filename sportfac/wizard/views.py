from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from profiles.models import FamilyUser

from .handlers import get_step_handler
from .models import WizardStep
from .workflow import WizardWorkflow


class BaseWizardStepView(View):
    """Base class for handling each step of the registration process."""

    template_name = None  # Should be defined in subclasses
    step_slug = None  # Should be defined in subclasses
    requires_completion = True  # Default behavior is to require completion

    def get_context_data(self, **kwargs):
        """Provide context data for rendering the step."""
        context = kwargs
        workflow = self.get_workflow()
        steps = workflow.get_visible_steps()
        total_steps = len(steps)
        current_step = self.get_step()
        current_index = next((index for index, step in enumerate(steps) if step.slug == self.step_slug), -1)
        progress_percent = ((current_index + 1) / total_steps) * 100 if total_steps > 0 else 0
        context["workflow"] = workflow
        context["steps"] = steps
        context["current_step"] = current_step
        context["total_steps"] = len(context["steps"])
        context["current_index"] = current_index + 1
        context["current_step_slug"] = current_step.slug
        context["progress_percent"] = progress_percent  # Pass the calculated progress to the template
        return context

    def get_step(self):
        """Retrieve the current step based on the `step_slug`."""
        return WizardStep.objects.get(slug=self.step_slug)

    def get_workflow(self):
        """Return the registration workflow for the current user."""
        registration_context = self.get_registration_context()
        user: FamilyUser = self.request.user  # noqa
        return WizardWorkflow(user, registration_context)

    def get_registration_context(self):
        """Return the registration context for evaluating the workflow."""
        # Implement context gathering logic based on user state
        user: FamilyUser = self.request.user  # noqa
        return {
            "user": user,
            # Add more context variables based on your business logic
        }

    def get_success_url(self):
        next_step = self.get_next_step()
        return reverse("wizard:step", kwargs={"step_slug": next_step.slug})

    def mark_step_complete(self):
        """Mark the current step as complete in the workflow."""
        handler = get_step_handler(self.get_step(), self.get_registration_context())
        handler.mark_complete()

    def get_next_step(self):
        """Determine the next step based on the workflow."""
        workflow = self.get_workflow()
        current_step = self.get_step()
        return workflow.get_next_step(current_step)


class FormStepView(BaseWizardStepView, FormView):
    """Class-based view for form steps in the registration process."""

    form_class = None  # Set the specific form class in subclasses

    def form_valid(self, form):
        """Handle form submission for the current step."""
        form.save()  # Save form data
        self.mark_step_complete()  # Mark the step as complete
        next_step = self.get_next_step()
        if next_step:
            return redirect(next_step.get_absolute_url())
        return redirect("registration_complete")


# Static/Template-Based Step
class StaticStepView(BaseWizardStepView, TemplateView):
    """Class-based view for static content or non-interactive steps."""

    template_name = "registration/static_step.html"  # Set the appropriate template

    def post(self, request, *args, **kwargs):
        """Handle navigation to the next step."""
        self.mark_step_complete()  # Mark the step as complete
        next_step = self.get_next_step()

        if next_step:
            return redirect(next_step.get_absolute_url())
        return redirect("registration_complete")


class EntryPointView(View):
    """
    Entry point for multi-step forms. Redirects based on user authentication status.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Redirect to the FamilyUser UpdateView
            return redirect("wizard:step", step_slug="user-update")
        return redirect("wizard:step", step_slug="user-create")


class ProfileCreationStepView(FormStepView):
    template_name = "registration/steps/profile_creation.html"
    # form_class = ProfileCreationForm  # Define your custom form class
    step_slug = "profile_creation"


class ChildrenStepView(StaticStepView):
    template_name = "wizard/children.html"
    step_slug = "children"