from django.conf.urls import patterns, url

from .views import ActivityDetailView, ActivityListView
from profiles.views import RegisteredActivitiesListView

urlpatterns = patterns('',
    url(r'^$', ActivityListView.as_view(), name='activities-list'),
    url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view()),
    url(r'^confirm/$', view=RegisteredActivitiesListView.as_view(), name="activities-confirm"),
    url(r'^(?P<slug>[-_\w]+)/$', view=ActivityDetailView.as_view(), name='activity-detail'),
) 