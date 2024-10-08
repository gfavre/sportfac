from django.urls import path

from profiles.views import WizardFamilyUserCreateView, WizardFamilyUserUpdateView
from .views import ActivitiesStepView, ChildrenStepView, EntryPointView


app_name = "wizard"
step_view_mapping = {
    "user-update": WizardFamilyUserUpdateView,
    "user-create": WizardFamilyUserCreateView,
    "children": ChildrenStepView,
    "activities": ActivitiesStepView,
}


# URL patterns
urlpatterns = [
    path("", lambda request: EntryPointView.as_view()(request), name="entry_point"),
    path(
        "steps/<slug:step_slug>/",
        lambda request, step_slug: step_view_mapping[step_slug].as_view()(request),
        name="step",
    ),
]
