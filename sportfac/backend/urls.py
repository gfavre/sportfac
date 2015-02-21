from django.conf.urls import patterns, include, url
from django.views.generic import TemplateView


import views

courses_patterns = patterns('', 
    url(r'^$', view=views.CourseListView.as_view(), 
        name='course-list'),
    url(r'^new$', view=views.CourseCreateView.as_view(), 
        name='course-create'),
    url(r'^(?P<course>[\w-]+)/$', view=views.CourseDetailView.as_view(), 
        name='course-detail'),
    url(r'^(?P<course>[\w-]+)/update$', view=views.CourseUpdateView.as_view(), 
        name='course-update'),
    url(r'^(?P<course>[\w-]+)/JS$', view=views.CourseJSCSVView.as_view(), 
        name='course-js-export'),
    url(r'^(?P<course>[\w-]+)/delete$', view=views.CourseDeleteView.as_view(),
        name='course-delete'),
    url(r'(?P<course>[\w-]+)/mail-responsible$', view=views.BackendMailCourseResponsibleView.as_view(),
        name='course-mail-responsible'),
    
    url(r'^(?P<course>[\w-]+)/participants$', view=views.CourseParticipantsView.as_view(), 
        name='course-participants'),     
        
        
        
)

activities_patterns = patterns('', 
    url(r'^$', view=views.ActivityListView.as_view(), 
        name='activity-list'),
    url(r'^new$', view=views.ActivityCreateView.as_view(), 
        name='activity-create'),
    url(r'^(?P<pk>\d+)/$', view=views.ActivityDetailView.as_view(), 
        name='activity-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.ActivityUpdateView.as_view(), 
        name='activity-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.ActivityDeleteView.as_view(),
        name='activity-delete'),
)

mail_patterns = patterns('', 
    url(r'^archive', view=views.MailArchiveListView.as_view(), 
        name='archive'),

    url(r'^need-confirmation', view=views.NeedConfirmationView.as_view(), 
        name='mail-needconfirmation'),
    url(r'^not-paid-yet', view=views.NotPaidYetView.as_view(), 
        name='mail-notpaidyet'),    
    url(r'^participants/(?P<course>[\w-]+)/custom$', 
        view=views.CustomMailParticipantsCreateView.as_view(),
        name="mail-participants-custom"),
    url(r'^participants/(?P<course>[\w-]+)/custom/preview$', 
        view=views.CustomMailParticipantsPreview.as_view(),
        name="mail-participants-custom-preview"),     
    url(r'^custom$', view=views.CustomUserCustomMailCreateView.as_view(),
        name='custom-mail-custom-users'),
    url(r'^custom/preview$', view=views.CustomUserCustomMailPreview.as_view(),
        name='custom-mail-custom-users-preview')
)

registrations_patterns = patterns('', 
    url(r'^$', view=views.RegistrationListView.as_view(), 
        name='registration-list'),
    url(r'^new$', view=views.RegistrationCreateView.as_view(), 
        name='registration-create'),
    url(r'^(?P<pk>\d+)/$', view=views.RegistrationDetailView.as_view(), 
        name='registration-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.RegistrationUpdateView.as_view(), 
        name='registration-update'),
    url(r'^(?P<pk>\d+)/cancel$', view=views.RegistrationDeleteView.as_view(),
        name='registration-delete'),
)

teachers_patterns = patterns('', 
    url(r'^$', view=views.TeacherListView.as_view(), 
        name='teacher-list'),
    url(r'^new$', view=views.TeacherCreateView.as_view(), 
        name='teacher-create'),
    url(r'^(?P<pk>\d+)/$', view=views.TeacherDetailView.as_view(), 
        name='teacher-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.TeacherUpdateView.as_view(), 
        name='teacher-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.TeacherDeleteView.as_view(),
        name='teacher-delete'),
)


users_patterns = patterns('', 
    url(r'^$', view=views.UserListView.as_view(), 
        name='user-list'),
    url(r'^managers$', view=views.ManagerListView.as_view(), 
        name='manager-list'),
    url(r'^responsible$', view=views.ResponsibleListView.as_view(), 
        name='responsible-list'),
    url(r'^new$', view=views.UserCreateView.as_view(), 
        name='user-create'),
    url(r'^manager/new$', view=views.ManagerCreateView.as_view(), 
        name='manager-create'),
    url(r'^(?P<pk>\d+)/$', view=views.UserDetailView.as_view(), 
        name='user-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.UserUpdateView.as_view(), 
        name='user-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.UserDeleteView.as_view(), 
        name='user-delete'),
    url(r'^(?P<pk>\d+)/pay$', view=views.UserPayUpdateView.as_view(), 
        name='user-pay'),    
    url(r'^(?P<user>\d+)/child/new$', view=views.ChildCreateView.as_view(), 
        name='child-create'),
    url(r'^(?P<user>\d+)/child/(?P<pk>\d+)/update$', view=views.ChildUpdateView.as_view(), 
        name='child-update'),
    url(r'^(?P<user>\d+)/child/(?P<pk>\d+)/delete$', view=views.ChildDeleteView.as_view(), 
        name='child-delete'),
)

urlpatterns = patterns('',
    url(r'^$', views.HomePageView.as_view(), name="home"),
    url(r'^dates$', views.RegistrationDatesView.as_view(), name='dates'),
    url(r'^activity/', include(activities_patterns)),
    url(r'^course/', include(courses_patterns)),
    url(r'^mail/', include(mail_patterns)),
    url(r'^registrations/', include(registrations_patterns)),
    url(r'^teacher/', include(teachers_patterns)),
    url(r'^user/', include(users_patterns)),   
)
