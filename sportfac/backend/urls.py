from django.conf import settings
from django.conf.urls import include, url

from . import views

activities_patterns = [
    url(r'^$', view=views.ActivityListView.as_view(),
        name='activity-list'),
    url(r'^new$', view=views.ActivityCreateView.as_view(),
        name='activity-create'),
    url(r'^(?P<activity>[\w-]+)/$', view=views.ActivityDetailView.as_view(),
        name='activity-detail'),
    url(r'^(?P<activity>[\w-]+)/update$', view=views.ActivityUpdateView.as_view(),
        name='activity-update'),
    url(r'^(?P<activity>[\w-]+)/delete$', view=views.ActivityDeleteView.as_view(),
        name='activity-delete'),
    url(r'^(?P<activity>[\w-]+)/absences', view=views.ActivityAbsenceView.as_view(),
        name='activity-absences'),
]

allocations_patterns = [
    url(r'^$', view=views.AllocationAccountListView.as_view(),
        name='allocation-list'),
    url(r'^report/$', view=views.AllocationAccountReportView.as_view(), name='allocation-report'),
    url(r'^new$', view=views.AllocationAccountCreateView.as_view(),
        name='allocation-create'),
    url(r'^(?P<pk>\d+)/update$', view=views.AllocationAccountUpdateView.as_view(),
        name='allocation-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.AllocationAccountDeleteView.as_view(),
        name='allocation-delete'),
]

courses_patterns = [
    url(r'^$', view=views.CourseListView.as_view(),
        name='course-list'),
    url(r'^absences$', view=views.CoursesAbsenceView.as_view(),
        name='courses-absence'),
    url(r'^new$', view=views.CourseCreateView.as_view(),
        name='course-create'),
    url(r'^(?P<course>[\w-]+)/$', view=views.CourseDetailView.as_view(),
        name='course-detail'),
    url(r'^(?P<course>[\w-]+)/export$', view=views.CourseParticipantsExportView.as_view(),
        name='course-xls-export'),
    url(r'^(?P<course>[\w-]+)/update$', view=views.CourseUpdateView.as_view(),
        name='course-update'),
    url(r'^(?P<course>[\w-]+)/absences$', view=views.CourseAbsenceView.as_view(),
        name='course-absence'),
    url(r'^(?P<course>[\w-]+)/JS$', view=views.CourseJSCSVView.as_view(),
        name='course-js-export'),
    url(r'^(?P<course>[\w-]+)/delete$', view=views.CourseDeleteView.as_view(),
        name='course-delete'),
    url(r'(?P<course>[\w-]+)/mail-instructors$', view=views.MailCourseInstructorsView.as_view(),
        name='course-mail-instructors'),
    url(r'(?P<course>[\w-]+)/mail-confirmation$', view=views.MailConfirmationParticipantsView.as_view(),
        name='course-mail-confirmation'),
    url(r'^(?P<course>[\w-]+)/participants$', view=views.CourseParticipantsView.as_view(),
        name='course-participants'),
]
if settings.KEPCHUP_FICHE_SALAIRE_MONTREUX:
    courses_patterns += [
        url(r'^(?P<course>[\w-]+)/pay/(?P<instructor>[0-9a-f\-]{32,})$', view=views.PaySlipMontreux.as_view(),
            name='pay-slip-montreux')]

mail_patterns = [
    url(r'^archive', view=views.MailArchiveListView.as_view(),
        name='archive'),
    url(r'^need-confirmation', view=views.NeedConfirmationView.as_view(),
        name='mail-needconfirmation'),
    url(r'^not-paid-yet', view=views.NotPaidYetView.as_view(),
        name='mail-notpaidyet'),
    url(r'^participants/(?P<course>[\w-]+)/custom$',
        view=views.ParticipantsMailCreateView.as_view(),
        name="mail-participants-custom"),
    url(r'^participants/(?P<course>[\w-]+)/custom/preview$',
        view=views.ParticipantsMailPreview.as_view(),
        name="mail-participants-custom-preview"),
    url(r'^custom$', view=views.MailCreateView.as_view(),
        name='custom-mail-custom-users'),
    url(r'^custom/preview$', view=views.MailPreview.as_view(),
        name='custom-mail-custom-users-preview')
]

registrations_patterns = [
    url(r'^$', view=views.RegistrationListView.as_view(),
        name='registration-list'),
    url(r'^export/xlsx', view=views.RegistrationExportView.as_view(),
        name='registration-export'),
    url(r'^new$', view=views.RegistrationCreateView.as_view(),
        name='registration-create'),
    url(r'^move$', view=views.RegistrationsMoveView.as_view(),
        name='registrations-move'),
    url(r'^registrations/validate-all$', view=views.RegistrationValidateView.as_view(),
        name='registrations-validate-all'),
    url(r'^(?P<pk>\d+)/$', view=views.RegistrationDetailView.as_view(),
        name='registration-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.RegistrationUpdateView.as_view(),
        name='registration-update'),
    url(r'^(?P<pk>\d+)/cancel$', view=views.RegistrationDeleteView.as_view(),
        name='registration-delete'),
    url(r'^bills$', view=views.BillListView.as_view(),
        name='bill-list'),
    url(r'^bills/(?P<pk>\d+)/$', view=views.BillDetailView.as_view(),
        name='bill-detail'),
    url(r'^bills/(?P<pk>\d+)/pay$', view=views.BillUpdateView.as_view(),
        name='bill-update'),
    url(r'^transport$', view=views.TransportListView.as_view(),
        name='transport-list'),
    url(r'^transport/(?P<pk>\d+)/$', view=views.TransportDetailView.as_view(),
        name='transport-detail'),
    url(r'^transport/(?P<pk>\d+)/update$', view=views.TransportUpdateView.as_view(),
        name='transport-update'),
    url(r'^transport/new$', view=views.TransportCreateView.as_view(),
        name='transport-create'),
    url(r'^transport/(?P<pk>\d+)/delete$', view=views.TransportDeleteView.as_view(),
        name='transport-delete'),
    url(r'^transport/move$', view=views.TransportMoveView.as_view(),
        name='transport-move'),
]

teachers_patterns = [
    url(r'^$', view=views.TeacherListView.as_view(),
        name='teacher-list'),
    url(r'^new$', view=views.TeacherCreateView.as_view(),
        name='teacher-create'),
    url(r'^import$', view=settings.KEPCHUP_USE_BUILDINGS and views.BuildingTeacherImportView.as_view() or
                          views.TeacherImportView.as_view(),
        name='teacher-import'),
    url(r'^(?P<pk>\d+)/$', view=views.TeacherDetailView.as_view(),
        name='teacher-detail'),
    url(r'^(?P<pk>\d+)/update$', view=views.TeacherUpdateView.as_view(),
        name='teacher-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.TeacherDeleteView.as_view(),
        name='teacher-delete'),
]

buildings_patterns = [
    url(r'^$', view=views.BuildingListView.as_view(),
        name='building-list'),
    url(r'^(?P<pk>\d+)/$', view=views.BuildingDetailView.as_view(),
        name='building-detail'),
    url(r'^new$', view=views.BuildingCreateView.as_view(),
        name='building-create'),
    url(r'^(?P<pk>\d+)/update$', view=views.BuildingUpdateView.as_view(),
        name='building-update'),
    url(r'^(?P<pk>\d+)/delete$', view=views.BuildingDeleteView.as_view(),
        name='building-delete'),
]

users_patterns = [
    url(r'^$', view=views.UserListView.as_view(),
        name='user-list'),
    url(r'^mail$', view=views.MailUsersView.as_view(), name='mail-users'),
    url(r'^export$', view=views.UserExportView.as_view(),
        name='user-export'),
    url(r'^managers$', view=views.ManagerListView.as_view(),
        name='manager-list'),
    url(r'^managers/export$', view=views.ManagerExportView.as_view(),
        name='manager-export'),
    url(r'^instructors$', view=views.InstructorListView.as_view(),
        name='instructor-list'),
    url(r'^instructors/export$', view=views.InstructorExportView.as_view(),
        name='instructor-export'),

    url(r'^new$', view=views.UserCreateView.as_view(),
        name='user-create'),
    url(r'^instructor/new$', view=views.InstructorCreateView.as_view(),
        name='instructor-create'),
    url(r'^manager/new$', view=views.ManagerCreateView.as_view(),
        name='manager-create'),

    url(r'^(?P<pk>[0-9a-f\-]{32,})/$', view=views.UserDetailView.as_view(),
        name='user-detail'),
    url(r'^(?P<pk>[0-9a-f\-]{32,})/instructor$', view=views.InstructorDetailView.as_view(),
        name='instructor-detail'),

    url(r'^(?P<pk>[0-9a-f\-]{32,})/update$', view=views.UserUpdateView.as_view(),
        name='user-update'),
    url(r'^(?P<pk>[0-9a-f\-]{32,})/delete$', view=views.UserDeleteView.as_view(),
        name='user-delete'),
    # url(r'^(?P<pk>\d+)/pay$', view=views.UserPayUpdateView.as_view(),
    #     name='user-pay'),
    url(r'^(?P<user>[0-9a-f\-]{32,})/password$', view=views.PasswordSetView.as_view(),
        name='password-change'),

    url(r'^(?P<user>[0-9a-f\-]{32,})/child/new$', view=views.ChildCreateView.as_view(),
        name='child-create'),

    url(r'^import$', view=views.ChildImportView.as_view(),
        name='child-import'),
]

children_patterns = [
    url(r'^$', view=views.ChildListView.as_view(), name='child-list'),
    url(r'^(?P<child>\d+)/$', view=views.ChildDetailView.as_view(), name='child-detail'),
    url(r'^new/$', view=views.ChildCreateView.as_view(), name='child-new'),

    url(r'^external/(?P<lagapeo>\d+)/$', view=views.ChildDetailView.as_view(), name='child-detail-lagapeo'),

    url(r'^(?P<child>\d+)/update$', view=views.ChildUpdateView.as_view(), name='child-update'),
    url(r'^(?P<child>\d+)/delete$', view=views.ChildDeleteView.as_view(), name='child-delete'),
    url(r'^(?P<child>\d+)/absences', view=views.ChildAbsencesView.as_view(), name='child-absences')

]

site_patterns = [
    url(r'^appointments$', view=views.AppointmentsManagementView.as_view(), name='appointments-manage'),

    url(r'^appointments/list$', view=views.AppointmentsListView.as_view(), name='appointments-list'),
    url(r'^appointments/export$', view=views.AppointmentsExportView.as_view(), name='appointments-export'),
    url(r'^appointments/(?P<appointment>[\d-]+)/delete$', view=views.AppointmentDeleteView.as_view(),
        name='appointment-delete'),
    url(r'emails$', view=views.GenericEmailListView.as_view(), name='emails-list'),
    url(r'emails/(?P<pk>\d+)/update$', view=views.GenericEmailUpdateView.as_view(), name='emails-update'),

    url(r'^$', view=views.FlatPageListView.as_view(), name='flatpages-list'),
    url(r'^(?P<pk>\d+)/update$', view=views.FlatPageUpdateView.as_view(), name='flatpages-update'),

]

payroll_patterns = [
    url(r'^$', view=views.PayrollReportView.as_view(), name='payroll-report'),
    url(r'^functions/$', view=views.FunctionListView.as_view(), name='function-list'),
    url(r'^functions/new$', view=views.FunctionCreateView.as_view(), name='function-create'),
    url(r'^functions/(?P<pk>\d+)/delete$', view=views.FunctionDeleteView.as_view(), name='function-delete'),
    url(r'^functions/(?P<pk>\d+)/update$', view=views.FunctionUpdateView.as_view(), name='function-update'),
]

years_patterns = [
    url(r'^$', view=views.YearListView.as_view(), name='year-list'),
    url(r'^(?P<pk>\d+)/update', view=views.YearUpdateView.as_view(), name='year-update'),
    url(r'^(?P<pk>\d+)/delete', view=views.YearDeleteView.as_view(), name='year-delete'),

    url(r'^new', view=views.YearCreateView.as_view(), name='year-create'),
    url(r'^change', view=views.ChangeYearFormView.as_view(), name='year-change'),
    url(r'^update', view=views.ChangeProductionYearFormView.as_view(), name='year-update'),

]

waiting_slots_patterns = [
    url(r'^(?P<pk>\d+)/transform$', view=views.WaitingSlotTransformView.as_view(),
        name='waiting_slot-transform'),
]


urlpatterns = [
    url(r'^$', views.HomePageView.as_view(), name="home"),
    url(r'^activity/', include(activities_patterns)),
    url(r'^allocations/', include(allocations_patterns)),
    url(r'^buildings/', include(buildings_patterns)),
    url(r'^child/', include(children_patterns)),
    url(r'^course/', include(courses_patterns)),
    url(r'^dates$', views.RegistrationDatesView.as_view(), name='dates'),
    url(r'^mail/', include(mail_patterns)),
    url(r'^payroll/', include(payroll_patterns)),
    url(r'^registrations/', include(registrations_patterns)),
    url(r'^teacher/', include(teachers_patterns)),
    url(r'^user/', include(users_patterns)),
    url(r'^site/', include(site_patterns)),
    url(r'^year/', include(years_patterns)),
    url(r'^waiting-slots/', include(waiting_slots_patterns)),
]
