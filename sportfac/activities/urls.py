from django.conf.urls import url
from django.contrib.sitemaps import  GenericSitemap

import views

from absences.views import AbsenceView
from .models import Activity

urlpatterns = [
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
    
    url(r'^courses/(?P<course>\d+)/send-infos$', 
        view=views.ResponsibleMailView.as_view(),
        name="mail-responsible"),
    
    url(r'^courses/(?P<course>\d+)/mail/preview$', 
        view=views.CustomMailPreview.as_view(),
        name="mail-preview"),
    
    url(r'^courses/(?P<course>\d+)/absences$', view=AbsenceView.as_view(), 
        name='course-absence'),

]

sitemap = GenericSitemap({'queryset': Activity.objects.all() })