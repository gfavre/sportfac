from django.urls import path

from activities.views import WizardQuestionsStepView
from appointments.views.register import WizardRentalStepView, WizardReturnStepView
from payments.views import WizardPaymentFailureView, WizardPaymentSuccessView
from profiles.views import WizardFamilyUserCreateView, WizardFamilyUserUpdateView
from registrations.views.wizard import WizardConfirmationStepView, WizardPaymentStepView
from .views import ActivitiesStepView, ChildrenStepView, EntryPointView, EquipmentStepView, QuestionsStepView


app_name = "wizard"
step_view_mapping = {
    "user-update": WizardFamilyUserUpdateView,
    "user-create": WizardFamilyUserCreateView,
    "children": ChildrenStepView,
    "activities": ActivitiesStepView,
    "questions": QuestionsStepView,
    "equipment": WizardRentalStepView,
    "equipment-need-return": EquipmentStepView,
    "equipment-return": WizardReturnStepView,
    "confirmation": WizardConfirmationStepView,
    "payment": WizardPaymentStepView,
    "payment-failure": WizardPaymentFailureView,
    "payment-success": WizardPaymentSuccessView,
}


# View function for entry point
def entry_point_view(request):
    return EntryPointView.as_view()(request)


# View function for handling dynamic steps
def step_view(request, step_slug):
    # Use WizardQuestionsStepView as the fallback if the step_slug is not found
    view_class = step_view_mapping.get(step_slug, WizardQuestionsStepView)
    return view_class.as_view()(request, step_slug=step_slug)


# URL patterns
urlpatterns = [
    path("", entry_point_view, name="entry_point"),
    path("steps/<slug:step_slug>/", step_view, name="step"),
]
