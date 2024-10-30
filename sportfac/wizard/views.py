from django.conf import settings
from django.db.models import Max, Min
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from activities.models import Course
from appointments.models import Rental
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser
from registrations.models import Bill as Invoice
from registrations.models import Registration
from .models import WizardStep
from .workflow import WizardWorkflow


class BaseWizardStepView(View):
    """Base class for handling each step of the registration process."""

    template_name = None  # Should be defined in subclasses
    step_slug = None  # Should be defined in subclasses
    requires_completion = True  # Default behavior is to require completion

    def get_step_slug(self):
        return self.step_slug

    def get_context_data(self, **kwargs):
        """Provide context data for rendering the step."""
        context = kwargs
        registration_context = self.get_registration_context()
        context.update(registration_context)
        workflow = self.get_workflow(registration_context)
        steps = workflow.get_visible_steps()
        total_steps = len(steps)
        current_step = self.get_step()
        current_index = next((index for index, step in enumerate(steps) if step.slug == self.get_step_slug()), -1)
        progress_percent = ((current_index + 1) / total_steps) * 100 if total_steps > 0 else 0
        context["workflow"] = workflow

        context["steps"] = steps
        context["current_step"] = current_step
        context["total_steps"] = len(context["steps"])
        context["current_index"] = current_index + 1
        context["current_step_slug"] = current_step.slug
        context["progress_percent"] = progress_percent  # Pass the calculated progress to the template
        context["next_step"] = self.get_next_step()
        context["previous_step"] = self.get_previous_step()

        context["success_url"] = self.get_success_url()
        return context

    def get_step(self):
        """Retrieve the current step based on the `step_slug`."""
        slug = self.get_step_slug()
        return WizardStep.objects.get(slug=slug)

    def get_workflow(self, registration_context=None):
        """Return the registration workflow for the current user."""
        if registration_context is None:
            registration_context = self.get_registration_context()
        user: FamilyUser = self.request.user  # noqa
        return WizardWorkflow(user, registration_context)

    def get_registration_context(self):
        """Return the registration context for evaluating the workflow."""
        # Implement context gathering logic based on user state
        user: FamilyUser = self.request.user  # noqa
        registrations = user.is_authenticated and Registration.waiting.filter(child__family=user) or []
        invoice = Invoice.objects.filter(family=user, status=Invoice.STATUS.waiting).first()
        context = {
            "user": user,
            "user_registered": user.is_authenticated,
            "has_children": user.is_authenticated and user.children.exists(),
            "has_registrations": len(registrations) > 0,
            "registrations": registrations,
            "invoice": invoice,
            "rentals": [],
            # Add more context variables based on your business logic
        }
        if settings.KEPCHUP_USE_APPOINTMENTS:
            context["rentals"] = Rental.objects.filter(child__family=user, paid=False)
        return context

    def get_success_url(self):
        next_step = self.get_next_step()
        if next_step:
            return reverse("wizard:step", kwargs={"step_slug": next_step.slug})
        return ""

    def get_previous_url(self):
        previous_step = self.get_previous_step()
        if previous_step:
            return reverse("wizard:step", kwargs={"step_slug": previous_step.slug})
        return ""

    def get_next_step(self):
        """Determine the next step based on the workflow."""
        workflow = self.get_workflow()
        current_step = self.get_step()
        return workflow.get_next_step(current_step)

    def get_previous_step(self):
        """Determine the previous step based on the workflow."""
        workflow = self.get_workflow()
        current_step = self.get_step()
        return workflow.get_previous_step(current_step)


# Static/Template-Based Step
class StaticStepView(BaseWizardStepView, TemplateView):
    """Class-based view for static content or non-interactive steps."""

    def post(self, request, *args, **kwargs):
        """Handle navigation to the next step."""
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


class ChildrenStepView(StaticStepView):
    template_name = "wizard/children.html"
    step_slug = "children"


class ActivitiesStepView(StaticStepView):
    template_name = "wizard/activities.html"
    step_slug = "activities"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["MAX_REGISTRATIONS"] = global_preferences_registry.manager()["MAX_REGISTRATIONS"]
        times = Course.objects.visible().aggregate(Max("end_time"), Min("start_time"))
        start_time = times["start_time__min"]
        end_time = times["end_time__max"]
        context["START_HOUR"] = start_time and start_time.hour - 1 or 8

        if end_time:
            if end_time.minute == 0:
                context["END_HOUR"] = end_time.hour
            else:
                context["END_HOUR"] = (end_time.hour + 1) % 24
        else:
            context["END_HOUR"] = 19
        return context
