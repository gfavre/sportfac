from django.urls import path

from profiles.views import WizardFamilyUserUpdateView

from .views import ChildrenStepView, EntryPointView


app_name = "wizard"
step_view_mapping = {
    "user-update": WizardFamilyUserUpdateView,
    "user-create": WizardFamilyUserUpdateView,
    "children": ChildrenStepView,
    "activities": ChildrenStepView,
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
