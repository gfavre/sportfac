from django.conf.urls import patterns, url, include
from django.contrib.auth import views as auth_views


from .forms import RegistrationForm, AuthenticationForm
from .views import (password_change, password_reset, RegistrationView, 
                    ChildrenListView, AccountView, BillingView, 
                    RegisteredActivitiesListView)


urlpatterns = patterns('',
    url(r'^$', AccountView.as_view(), name="profiles_account"),
    url(r'^children/$', ChildrenListView.as_view(), name="profiles_children"),
    url(r'^summary/$', BillingView.as_view(template_name="profiles/summary.html"), name="profiles_registered_activities"),
    url(r'^register/$',  RegistrationView.as_view(), name="registeraccount"),
    url(r'^payement/$', BillingView.as_view(wizard=False), name="profiles_billing"),
    
    url(r'^reset/$', password_reset, name="registration_reset"),
    url(r'^password/change/$', password_change, name='password_change'),
    url(r'^password/change/done/$', auth_views.password_change_done, name='password_change_done'),
    url(r'^password/reset/$', password_reset, name='password_reset'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        name='password_reset_done'),
    url(r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        name='password_reset_complete'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        name='password_reset_confirm'),
    url(r'^login/$', auth_views.login,
        {'template_name': 'registration/login.html', 'authentication_form': AuthenticationForm}, 
        name='auth_login'),
    url(r'^logout/$', auth_views.logout,
        {'template_name': 'registration/logout.html'},
        name='auth_logout'),
     
    
    #and now add the registration urls
    url(r'', include('registration.backends.default.urls')),
)
