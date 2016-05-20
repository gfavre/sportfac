from django.conf.urls import include, url

from rest_framework.routers import DefaultRouter, SimpleRouter

from . import  views

router = DefaultRouter()
router.register(r'absences', views.AbsenceViewSet, base_name='absence')
router.register(r'activities', views.ActivityViewSet, base_name='activity')
router.register(r'courses', views.CourseViewSet, base_name='course')
router.register(r'children', views.ChildrenViewSet, base_name='child')
router.register(r'teachers', views.TeacherViewSet, base_name='teacher')
router.register(r'registrations', views.RegistrationViewSet, base_name='registration')
router.register(r'extra', views.ExtraInfoViewSet, base_name="api-extra")
router.register(r'all-children', views.SimpleChildrenViewSet, base_name='allchildren')



#router.register(r'family', views.FamilyView)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^family/', views.FamilyView.as_view()),

    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]