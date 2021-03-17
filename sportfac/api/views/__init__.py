# -*- coding: utf-8 -*-
from .absence_views import AbsenceViewSet, SessionViewSet
from .activities_views import ActivityViewSet, CourseViewSet, ChangeCourse
from .dashboard_views import DashboardFamilyView, DashboardInstructorsView, DashboardManagersView
from .family_views import ChildrenViewSet, ChildActivityLevelViewSet, FamilyView, SimpleChildrenViewSet
from .registration_views import BuildingViewSet, ExtraInfoViewSet, RegistrationViewSet, TeacherViewSet, YearViewSet