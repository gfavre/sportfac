from django.urls import path

from activities.views import WizardQuestionsStepView
from profiles.views import WizardFamilyUserCreateView, WizardFamilyUserUpdateView
from .views import ActivitiesStepView, ChildrenStepView, EntryPointView


app_name = "wizard"
step_view_mapping = {
    "user-update": WizardFamilyUserUpdateView,
    "user-create": WizardFamilyUserCreateView,
    "children": ChildrenStepView,
    "activities": ActivitiesStepView,
}


def get_step_view(step_slug):
    try:
        return step_view_mapping[step_slug].as_view()
    except KeyError:
        return WizardQuestionsStepView.as_view()


# URL patterns
urlpatterns = [
    path("", lambda request: EntryPointView.as_view()(request), name="entry_point"),
    path(
        "steps/<slug:step_slug>/",
        lambda request, step_slug: get_step_view(step_slug)(request, step_slug=step_slug),
        name="step",
    ),
]
