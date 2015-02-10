from django.conf.urls import patterns, url
from django.contrib.sitemaps import  GenericSitemap

import views

from .models import Activity

urlpatterns = patterns('',
    url(r'^(?P<pk>\d+)/$', view=views.ActivityDetailView.as_view()),
    url(r'^(?P<slug>[-_\w]+)/$', view=views.ActivityDetailView.as_view(), 
        name='activity-detail'),
    url(r'^my-courses$', view=views.MyCoursesListView.as_view(), 
        name='my-courses'),
    url(r'^courses/(?P<course>\d+)/$', view=views.MyCourseDetailView.as_view(), 
        name='course-detail'),
    url(r'^courses/(?P<course>\d+)/mail$', 
        view=views.CustomMailCreateView.as_view(),
        name="mail-participants-custom"),
    url(r'^courses/(?P<course>\d+)/mail/preview$', 
        view=views.CustomMailPreview.as_view(),
        name="mail-preview"),


) 

sitemap = GenericSitemap({'queryset': Activity.objects.all() })