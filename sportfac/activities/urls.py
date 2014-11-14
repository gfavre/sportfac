from django.conf.urls import patterns, url
from django.contrib.sitemaps import  GenericSitemap

from .views import ActivityDetailView, ActivityListView
from .models import Activity

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view()),
    url(r'^(?P<slug>[-_\w]+)/$', view=ActivityDetailView.as_view(), name='activity-detail'),
) 

sitemap = GenericSitemap({'queryset': Activity.objects.all() })