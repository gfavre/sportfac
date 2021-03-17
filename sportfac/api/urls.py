# -*- coding:utf-8 -*-
from django.conf.urls import include, url

from rest_framework.routers import DefaultRouter

from . import views
from appointments.views import api_views as appointment_views

router = DefaultRouter()
router.register(r'sessions', views.SessionViewSet, base_name='session')
router.register(r'absences', views.AbsenceViewSet, base_name='absence')
router.register(r'activities', views.ActivityViewSet, base_name='activity')
router.register(r'courses', views.CourseViewSet, base_name='course')
router.register(r'children', views.ChildrenViewSet, base_name='child')
router.register(r'teachers', views.TeacherViewSet, base_name='teacher')
router.register(r'buildings', views.BuildingViewSet, base_name='building')
router.register(r'registrations', views.RegistrationViewSet, base_name='registration')
router.register(r'levels', views.ChildActivityLevelViewSet, base_name='level')

router.register(r'extra', views.ExtraInfoViewSet, base_name="api-extra")
router.register(r'years', views.YearViewSet, base_name="year")

router.register(r'all-children', views.SimpleChildrenViewSet, base_name='allchildren')
router.register('all-slots', appointment_views.SlotsViewset, base_name='slots')

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^family/', views.FamilyView.as_view(), name='family-list'),
    url(r'^change-course/$', views.ChangeCourse.as_view(), name='change-course'),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^dashboard/users/', views.DashboardFamilyView.as_view(), name='all_users'),
    url(r'^dashboard/instructors/', views.DashboardInstructorsView.as_view(), name='all_instructors'),
    url(r'^dashboard/instructors/', views.DashboardManagersView.as_view(), name='all_instructors'),
    url(r'^appointments/slots/$', appointment_views.SlotsList.as_view(), name='all_slots'),
    url(r'^appointments/slots/(?P<slot_id>\d+)/', appointment_views.RegisterSlot.as_view(),
        name='register_slots'),

]
