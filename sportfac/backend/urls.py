from django.conf.urls import patterns, include, url

from .views import CourseCreateView, CourseDeleteView, CourseDetailView, \
                   CourseListView, CourseUpdateView

courses_patterns = patterns('', 
    url(r'^$', view=CourseListView.as_view(), 
        name='course-list'),
    url(r'^new$', view=CourseCreateView.as_view(), 
        name='course-create'),
    url(r'^(?P<pk>\d+)/$', view=CourseDetailView.as_view(), 
        name='course-detail'),
    url(r'^(?P<pk>\d+)/update$', view=CourseUpdateView.as_view(), 
        name='course-update'),
    url(r'^(?P<pk>\d+)/delete$', view=CourseDeleteView.as_view(),
        name='course-delete'),

)


urlpatterns = patterns('',
    url(r'^course/', include(courses_patterns)),

)
