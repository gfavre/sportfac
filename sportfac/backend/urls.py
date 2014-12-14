from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView

from .views import CourseCreateView, CourseDeleteView, CourseDetailView, \
                   CourseListView, CourseUpdateView,\
                   ActivityCreateView, ActivityDeleteView, ActivityDetailView, \
                   ActivityListView, ActivityUpdateView,\
                   ResponsibleCreateView, ResponsibleDeleteView, ResponsibleDetailView, \
                   ResponsibleListView, ResponsibleUpdateView, \
                   RegistrationCreateView, RegistrationDeleteView, RegistrationDetailView, \
                   RegistrationListView, RegistrationUpdateView, \
                   RegistrationDatesView, HomePageView

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

responsibles_patterns = patterns('', 
    url(r'^$', view=ResponsibleListView.as_view(), 
        name='responsible-list'),
    url(r'^new$', view=ResponsibleCreateView.as_view(), 
        name='responsible-create'),
    url(r'^(?P<pk>\d+)/$', view=ResponsibleDetailView.as_view(), 
        name='responsible-detail'),
    url(r'^(?P<pk>\d+)/update$', view=ResponsibleUpdateView.as_view(), 
        name='responsible-update'),
    url(r'^(?P<pk>\d+)/delete$', view=ResponsibleDeleteView.as_view(),
        name='responsible-delete'),
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

registrations_patterns = patterns('', 
    url(r'^$', view=RegistrationListView.as_view(), 
        name='registration-list'),
    url(r'^new$', view=RegistrationCreateView.as_view(), 
        name='registration-create'),
    url(r'^(?P<pk>\d+)/$', view=RegistrationDetailView.as_view(), 
        name='registration-detail'),
    url(r'^(?P<pk>\d+)/update$', view=RegistrationUpdateView.as_view(), 
        name='registration-update'),
    url(r'^(?P<pk>\d+)/cancel$', view=RegistrationDeleteView.as_view(),
        name='registration-delete'),
)




urlpatterns = patterns('',
    url(r'^$', HomePageView.as_view(), name="home"),
    url(r'^dates$', RegistrationDatesView.as_view(), name='dates'),
    url(r'^activity/', include(activities_patterns)),
    url(r'^course/', include(courses_patterns)),
    url(r'^registrations/', include(registrations_patterns)),
    url(r'^responsible/', include(responsibles_patterns)),
)
