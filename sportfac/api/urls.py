from django.conf.urls import patterns, include, url

from rest_framework.routers import DefaultRouter, SimpleRouter

from . import  views

router = DefaultRouter()
router.register(r'activities', views.ActivityViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'children', views.ChildrenViewSet)
router.register(r'teachers', views.TeacherViewSet)

#router.register(r'family', views.FamilyView)

urlpatterns = patterns('',
    url(r'^', include(router.urls)),
    url(r'^family/', views.FamilyView.as_view()),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
)