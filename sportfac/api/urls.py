from django.urls import include, path

from rest_framework.routers import DefaultRouter

from appointments.views import api_views as appointment_views
from . import views


app_name = "api"

router = DefaultRouter()
router.register("absences", views.AbsenceViewSet, basename="absence")
router.register("activities", views.ActivityViewSet, basename="activity")
router.register("buildings", views.BuildingViewSet, basename="building")
router.register("children", views.ChildrenViewSet, basename="child")
router.register("courses", views.CourseViewSet, basename="course")
router.register("courses-instructors", views.CourseInstructorsViewSet, basename="course-instructors")
router.register("levels", views.ChildActivityLevelViewSet, basename="level")
router.register("registrations", views.RegistrationViewSet, basename="registration")
router.register("rentals", appointment_views.RentalViewSet, basename="rental")
router.register("sessions", views.SessionViewSet, basename="session")
router.register("teachers", views.TeacherViewSet, basename="teacher")
router.register("waiting_slots", views.WaitingSlotViewSet, basename="waiting_slot")

router.register("extra", views.OldExtraInfoViewSet, basename="api-extra")  # DEPRECATED
router.register("extra-infos", views.ExtraInfoViewSet, basename="api-extra-infos")

router.register("years", views.YearViewSet, basename="year")

router.register("all-children", views.SimpleChildrenViewSet, basename="allchildren")
router.register("all-slots", appointment_views.SlotsViewset, basename="slots")

urlpatterns = [
    path("", include(router.urls)),
    path("family/", views.FamilyView.as_view(), name="family-list"),
    path("change-course/", views.ChangeCourse.as_view(), name="change-course"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("dashboard/users/", views.DashboardFamilyView.as_view(), name="all_users"),
    path(
        "dashboard/instructors/",
        views.DashboardInstructorsView.as_view(),
        name="all_instructors",
    ),
    path("dashboard/managers/", views.DashboardManagersView.as_view(), name="all_managers"),
    path(
        "appointments/rentals/<int:slot_id>/",
        appointment_views.AppointmentManagementView.as_view(),
        name="appointments-management",
    ),
    path("appointments/slots/", appointment_views.SlotsList.as_view(), name="all_slots"),
    path(
        "appointments/slots/<int:slot_id>/",
        appointment_views.RegisterSlot.as_view(),
        name="register_slots",
    ),
    path("appointments/register", appointment_views.RegisterChildrenToSlotView.as_view(), name="appointment-register"),
    path(
        "appointments/unregister", appointment_views.RemoveChildFromSlotView.as_view(), name="appointment-unregister"
    ),
]
