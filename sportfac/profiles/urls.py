from django.conf.urls import patterns, url, include


from .forms import RegistrationForm
from .views import MyRegistrationView, ChildrenListView


urlpatterns = patterns('',
    url(r'^children/$', ChildrenListView.as_view(), name="profiles_children"),
    url(r'^register/$', MyRegistrationView.as_view(), name='registration_register'),
    (r'', include('registration.backends.simple.urls')),
    
    
    #url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view()),
    #url(r'^(?P<slug>[-_\w]+)/$', view=ActivityDetailView.as_view(), name='activity-detail'),
) 