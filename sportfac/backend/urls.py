from django.conf.urls import patterns, include, url

from .views import CourseDetailView

urlpatterns = patterns('',
    url(r'^course/(?P<pk>\d+)/$', view=CourseDetailView.as_view()),
)