from django.conf.urls import patterns, url

from .views import ActivityDetailView, ActivityListView

urlpatterns = patterns('',
    url(r'^register/$', ActivityListView.as_view(), name='activities-list'),
    url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view()),
    url(r'^(?P<slug>[-_\w]+)/$', view=ActivityDetailView.as_view(), name='activity-detail'),
) 