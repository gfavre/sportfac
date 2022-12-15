# -*- coding:utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import include, url

from appointments.views import api_views as appointment_views
from rest_framework.routers import DefaultRouter

from . import views


app_name = "api"

router = DefaultRouter()
router.register(r"sessions", views.SessionViewSet, basename="session")
router.register(r"absences", views.AbsenceViewSet, basename="absence")
router.register(r"activities", views.ActivityViewSet, basename="activity")
router.register(r"courses", views.CourseViewSet, basename="course")
router.register(
    r"courses-instructors", views.CourseInstructorsViewSet, basename="course-instructors"
)
router.register(r"children", views.ChildrenViewSet, basename="child")
router.register(r"teachers", views.TeacherViewSet, basename="teacher")
router.register(r"buildings", views.BuildingViewSet, basename="building")
router.register(r"registrations", views.RegistrationViewSet, basename="registration")
router.register(r"levels", views.ChildActivityLevelViewSet, basename="level")
router.register(r"waiting_slots", views.WaitingSlotViewSet, basename="waiting_slot")

router.register(r"extra", views.ExtraInfoViewSet, basename="api-extra")
router.register(r"years", views.YearViewSet, basename="year")

router.register(r"all-children", views.SimpleChildrenViewSet, basename="allchildren")
router.register("all-slots", appointment_views.SlotsViewset, basename="slots")

urlpatterns = [
    url(r"^", include(router.urls)),
    url(r"^family/", views.FamilyView.as_view(), name="family-list"),
    url(r"^change-course/$", views.ChangeCourse.as_view(), name="change-course"),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"^dashboard/users/", views.DashboardFamilyView.as_view(), name="all_users"),
    url(
        r"^dashboard/instructors/",
        views.DashboardInstructorsView.as_view(),
        name="all_instructors",
    ),
    url(r"^dashboard/managers/", views.DashboardManagersView.as_view(), name="all_managers"),
    url(r"^appointments/slots/$", appointment_views.SlotsList.as_view(), name="all_slots"),
    url(
        r"^appointments/slots/(?P<slot_id>\d+)/",
        appointment_views.RegisterSlot.as_view(),
        name="register_slots",
    ),
]
