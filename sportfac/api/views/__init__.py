# -*- coding: utf-8 -*-
from .absence_views import AbsenceViewSet, SessionViewSet
from .activities_views import (
    ActivityViewSet,
    ChangeCourse,
    CourseInstructorsViewSet,
    CourseViewSet,
)
from .dashboard_views import DashboardFamilyView, DashboardInstructorsView, DashboardManagersView
from .family_views import (
    ChildActivityLevelViewSet,
    ChildrenViewSet,
    FamilyView,
    SimpleChildrenViewSet,
)
from .registration_views import (
    BuildingViewSet,
    ExtraInfoViewSet,
    RegistrationViewSet,
    TeacherViewSet,
    YearViewSet,
)
from .waiting_slots_views import WaitingSlotViewSet
