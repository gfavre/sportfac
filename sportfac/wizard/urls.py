from django.urls import path

from .views import ChildrenStepView


app_name = "wizard"
step_view_mapping = {
    "children": ChildrenStepView,
}


# URL patterns
urlpatterns = [
    path(
        "steps/<slug:step_slug>/",
        lambda request, step_slug: step_view_mapping[step_slug].as_view()(request),
        name="registration_step",
    ),
]
