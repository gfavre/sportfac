from django.conf.urls import patterns, url, include
from django.contrib.auth.views import password_reset


from .forms import RegistrationForm
from .views import MyRegistrationView, ChildrenListView, AccountView, BillingView, RegisteredActivitiesListView


urlpatterns = patterns('',
    url(r'^$', AccountView.as_view(), name="profiles_account"),
    url(r'^children/$', ChildrenListView.as_view(), name="profiles_children"),
    url(r'^reset/$', password_reset, name="registration_reset"),
    url(r'^summary/$', BillingView.as_view(template_name="profiles/summary.html"), name="profiles_registered_activities"),

    (r'', include('registration.backends.simple.urls')),
    
    
    #url(r'^(?P<pk>\d+)/$', view=ActivityDetailView.as_view()),
    #url(r'^(?P<slug>[-_\w]+)/$', view=ActivityDetailView.as_view(), name='activity-detail'),
) 