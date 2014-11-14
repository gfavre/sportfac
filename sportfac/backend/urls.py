from django.conf.urls import patterns, include, url

from .views import CourseCreateView, CourseDeleteView, CourseDetailView, \
                   CourseListView, CourseUpdateView,\
                   ActivityCreateView, ActivityDeleteView, ActivityDetailView, \
                   ActivityListView, ActivityUpdateView

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

activities_patterns = patterns('', 
    url(r'^$', view=ActivityListView.as_view(), 
        name='activity-list'),
    url(r'^new$', view=ActivityCreateView.as_view(), 
        name='activity-create'),
    url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view(), 
        name='activity-detail'),
    url(r'^(?P<pk>\d+)/update$', view=ActivityUpdateView.as_view(), 
        name='activity-update'),
    url(r'^(?P<pk>\d+)/delete$', view=ActivityDeleteView.as_view(),
        name='activity-delete'),
)



urlpatterns = patterns('',
    url(r'^course/', include(courses_patterns)),
    url(r'^activity/', include(activities_patterns)),

)
