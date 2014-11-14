from django.conf.urls import patterns, include, url

from .views import CourseCreateView, CourseDetailView

courses_patterns = patterns('', 
    url(r'^new$', view=CourseCreateView.as_view()),
    url(r'^(?P<pk>\d+)/$', view=CourseDetailView.as_view()),
)


urlpatterns = patterns('',
    url(r'^course/', include(courses_patterns)),

)
