from django.conf.urls import url
from django.contrib.sitemaps import GenericSitemap

import views

from absences.views import AbsenceCourseView
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

    url(r'^courses/(?P<course>\d+)/mail/select$',
        view=views.MailUsersView.as_view(),
        name="select-participants"),

    url(r'^courses/(?P<course>\d+)/mail/custom',
        view=views.CustomParticipantsCustomMailView.as_view(),
        name="mail-custom-participants-custom"),

    url(r'^courses/(?P<course>\d+)/send-infos$',
        view=views.MailCourseInstructorsView.as_view(),
        name="mail-instructors"),
    
    url(r'^courses/(?P<course>\d+)/mail/preview$', 
        view=views.CustomMailPreview.as_view(),
        name="mail-preview"),
    
    url(r'^courses/(?P<course>\d+)/absences/$', view=AbsenceCourseView.as_view(),
        name='course-absence'),
    url(r'^pay-slips/(?P<pk>[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12})/',
        view=views.PaySlipDetailView.as_view(),
        name='payslip-detail'),

]

sitemap = GenericSitemap({'queryset': Activity.objects.all() })