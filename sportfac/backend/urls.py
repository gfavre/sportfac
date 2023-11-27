from django.conf import settings
from django.urls import include, path

from . import views


app_name = "backend"

activities_patterns = [
    path("", view=views.ActivityListView.as_view(), name="activity-list"),
    path("new", view=views.ActivityCreateView.as_view(), name="activity-create"),
    path("<slug:activity>", view=views.ActivityDetailView.as_view(), name="activity-detail"),
    path(
        "<slug:activity>/update",
        view=views.ActivityUpdateView.as_view(),
        name="activity-update",
    ),
    path(
        "<slug:activity>/delete",
        view=views.ActivityDeleteView.as_view(),
        name="activity-delete",
    ),
    path(
        "<slug:activity>/absences",
        view=views.ActivityAbsenceView.as_view(),
        name="activity-absences",
    ),
]

allocations_patterns = [
    path("", view=views.AllocationAccountListView.as_view(), name="allocation-list"),
    path("report/", view=views.AllocationAccountReportView.as_view(), name="allocation-report"),
    path("new", view=views.AllocationAccountCreateView.as_view(), name="allocation-create"),
    path(
        "<int:pk>update",
        view=views.AllocationAccountUpdateView.as_view(),
        name="allocation-update",
    ),
    path(
        "<int:pk>/delete",
        view=views.AllocationAccountDeleteView.as_view(),
        name="allocation-delete",
    ),
]

courses_patterns = [
    path("", view=views.CourseListView.as_view(), name="course-list"),
    path("absences", view=views.CoursesAbsenceView.as_view(), name="courses-absence"),
    path("export/xlsx", view=views.CoursesExportView.as_view(), name="courses-export"),
    path("new", view=views.CourseCreateView.as_view(), name="course-create"),
    path("mail-confirmation", view=views.MailConfirmationCoursesView.as_view(), name="courses-mail-confirmation"),
    path("mail-instructors", view=views.MailInstructorsCoursesView.as_view(), name="courses-mail-instructors"),
    path("visibility", view=views.CoursesToggleVisibilityView.as_view(), name="courses-toggle-visibility"),
    path("<slug:course>/", view=views.CourseDetailView.as_view(), name="course-detail"),
    path(
        "<slug:course>/export",
        view=views.CourseParticipantsExportView.as_view(),
        name="course-xls-export",
    ),
    path("<slug:course>/update", view=views.CourseUpdateView.as_view(), name="course-update"),
    path(
        "<slug:course>/absences",
        view=views.CourseAbsenceView.as_view(),
        name="course-absence",
    ),
    path("<slug:course>/JS", view=views.CourseJSCSVView.as_view(), name="course-js-export"),
    path("<slug:course>/delete", view=views.CourseDeleteView.as_view(), name="course-delete"),
    path(
        "<slug:course>/mail-instructors",
        view=views.MailCourseInstructorsView.as_view(),
        name="course-mail-instructors",
    ),
    path(
        "<slug:course>/mail-confirmation",
        view=views.MailConfirmationParticipantsView.as_view(),
        name="course-mail-confirmation",
    ),
    path(
        "<slug:course>/participants",
        view=views.CourseParticipantsView.as_view(),
        name="course-participants",
    ),
]

if settings.KEPCHUP_FICHE_SALAIRE_MONTREUX:
    courses_patterns += [
        path(
            "<slug:course>/pay/<uuid:instructor>",
            view=views.PaySlipMontreux.as_view(),
            name="pay-slip-montreux",
        )
    ]

mail_patterns = [
    path("archive", view=views.MailArchiveListView.as_view(), name="archive"),
    path(
        "need-confirmation",
        view=views.NeedConfirmationView.as_view(),
        name="mail-needconfirmation",
    ),
    path("not-paid-yet", view=views.NotPaidYetView.as_view(), name="mail-notpaidyet"),
    path(
        "participants/<course>/custom",
        view=views.ParticipantsMailCreateView.as_view(),
        name="mail-participants-custom",
    ),
    path(
        "participants/<course>/custom/preview",
        view=views.ParticipantsMailPreview.as_view(),
        name="mail-participants-custom-preview",
    ),
    path("custom", view=views.MailCreateView.as_view(), name="custom-mail-custom-users"),
    path("custom/preview", view=views.MailPreview.as_view(), name="custom-mail-custom-users-preview"),
]

registrations_patterns = [
    path("", view=views.RegistrationListView.as_view(), name="registration-list"),
    path("export/xlsx", view=views.RegistrationExportView.as_view(), name="registration-export"),
    path("new", view=views.RegistrationCreateView.as_view(), name="registration-create"),
    path("move", view=views.RegistrationsMoveView.as_view(), name="registrations-move"),
    path(
        "registrations/validate-all",
        view=views.RegistrationValidateView.as_view(),
        name="registrations-validate-all",
    ),
    path("<int:pk>/", view=views.RegistrationDetailView.as_view(), name="registration-detail"),
    path(
        "<int:pk>/update",
        view=views.RegistrationUpdateView.as_view(),
        name="registration-update",
    ),
    path(
        "<int:pk>/cancel",
        view=views.RegistrationDeleteView.as_view(),
        name="registration-delete",
    ),
    path("bills", view=views.BillListView.as_view(), name="bill-list"),
    path("bills/<int:pk>/", view=views.BillDetailView.as_view(), name="bill-detail"),
    path("bills/<int:pk>/pay", view=views.BillUpdateView.as_view(), name="bill-update"),
    path("transport", view=views.TransportListView.as_view(), name="transport-list"),
    path("transport/<int:pk>/", view=views.TransportDetailView.as_view(), name="transport-detail"),
    path(
        "transport/<int:pk>/update",
        view=views.TransportUpdateView.as_view(),
        name="transport-update",
    ),
    path("transport/new", view=views.TransportCreateView.as_view(), name="transport-create"),
    path(
        "transport/<int:pk>/delete",
        view=views.TransportDeleteView.as_view(),
        name="transport-delete",
    ),
    path("transport/move", view=views.TransportMoveView.as_view(), name="transport-move"),
]

teachers_patterns = [
    path("", view=views.TeacherListView.as_view(), name="teacher-list"),
    path("new", view=views.TeacherCreateView.as_view(), name="teacher-create"),
    path(
        "import",
        view=settings.KEPCHUP_USE_BUILDINGS
        and views.BuildingTeacherImportView.as_view()
        or views.TeacherImportView.as_view(),
        name="teacher-import",
    ),
    path("<int:pk>/", view=views.TeacherDetailView.as_view(), name="teacher-detail"),
    path("<int:pk>/update", view=views.TeacherUpdateView.as_view(), name="teacher-update"),
    path("<int:pk>/delete", view=views.TeacherDeleteView.as_view(), name="teacher-delete"),
]

buildings_patterns = [
    path("", view=views.BuildingListView.as_view(), name="building-list"),
    path("<int:pk>/", view=views.BuildingDetailView.as_view(), name="building-detail"),
    path("new", view=views.BuildingCreateView.as_view(), name="building-create"),
    path("<int:pk>/update", view=views.BuildingUpdateView.as_view(), name="building-update"),
    path("<int:pk>/delete", view=views.BuildingDeleteView.as_view(), name="building-delete"),
]


users_patterns = [
    path("", view=views.UserListView.as_view(), name="user-list"),
    path("mail", view=views.MailUsersView.as_view(), name="mail-users"),
    path("export", view=views.UserExportView.as_view(), name="user-export"),
    path("managers", view=views.ManagerListView.as_view(), name="manager-list"),
    path("managers/export", view=views.ManagerExportView.as_view(), name="manager-export"),
    path("instructors", view=views.InstructorListView.as_view(), name="instructor-list"),
    path(
        "instructors/export",
        view=views.InstructorExportView.as_view(),
        name="instructor-export",
    ),
    path("new", view=views.UserCreateView.as_view(), name="user-create"),
    path("instructor/new", view=views.InstructorCreateView.as_view(), name="instructor-create"),
    path("manager/new", view=views.ManagerCreateView.as_view(), name="manager-create"),
    path("<uuid:pk>/", view=views.UserDetailView.as_view(), name="user-detail"),
    path(
        "<uuid:pk>/instructor",
        view=views.InstructorDetailView.as_view(),
        name="instructor-detail",
    ),
    path(
        "<uuid:pk>/update",
        view=views.UserUpdateView.as_view(),
        name="user-update",
    ),
    path(
        "<uuid:pk>/delete",
        view=views.UserDeleteView.as_view(),
        name="user-delete",
    ),
    # path('<int:pk>/pay', view=views.UserPayUpdateView.as_view(),
    #     name='user-pay'),
    path(
        "<uuid:user>/password",
        view=views.PasswordSetView.as_view(),
        name="password-change",
    ),
    path(
        "<uuid:user>/child/new",
        view=views.ChildCreateView.as_view(),
        name="child-create",
    ),
    path("import/", view=views.ChildImportView.as_view(), name="child-import"),
]

children_patterns = [
    path("", view=views.ChildListView.as_view(), name="child-list"),
    path("<int:child>/", view=views.ChildDetailView.as_view(), name="child-detail"),
    path("new/", view=views.ChildCreateView.as_view(), name="child-new"),
    path(
        "external/<int:lagapeo>/",
        view=views.ChildDetailView.as_view(),
        name="child-detail-lagapeo",
    ),
    path("<int:child>/update", view=views.ChildUpdateView.as_view(), name="child-update"),
    path("<int:child>/delete", view=views.ChildDeleteView.as_view(), name="child-delete"),
    path(
        "child/<int:child>/absences",
        view=views.ChildAbsencesView.as_view(),
        name="child-absences",
    ),
]

site_patterns = [
    path(
        "appointments",
        view=views.AppointmentsManagementView.as_view(),
        name="appointments-manage",
    ),
    path("appointments/list", view=views.AppointmentsListView.as_view(), name="appointments-list"),
    path(
        "appointments/export",
        view=views.AppointmentsExportView.as_view(),
        name="appointments-export",
    ),
    path(
        "appointments/<int:appointment>/delete",
        view=views.AppointmentDeleteView.as_view(),
        name="appointment-delete",
    ),
    path("emails", view=views.GenericEmailListView.as_view(), name="emails-list"),
    path(
        "emails/<int:pk>/update",
        view=views.GenericEmailUpdateView.as_view(),
        name="emails-update",
    ),
    path("<int:pk>/update", view=views.FlatPageUpdateView.as_view(), name="flatpages-update"),
    path("", view=views.FlatPageListView.as_view(), name="flatpages-list"),
]

payroll_patterns = [
    path("", view=views.PayrollReportView.as_view(), name="payroll-report"),
    path("roles/", view=views.SupervisorRolesList.as_view(), name="roles-list"),
    path("functions/", view=views.FunctionListView.as_view(), name="function-list"),
    path("functions/new", view=views.FunctionCreateView.as_view(), name="function-create"),
    path(
        "functions/<int:pk>/delete",
        view=views.FunctionDeleteView.as_view(),
        name="function-delete",
    ),
    path(
        "functions/<int:pk>/update",
        view=views.FunctionUpdateView.as_view(),
        name="function-update",
    ),
]

years_patterns = [
    path("", view=views.YearListView.as_view(), name="year-list"),
    path("<int:pk>/update", view=views.YearUpdateView.as_view(), name="year-update"),
    path("<int:pk>/delete", view=views.YearDeleteView.as_view(), name="year-delete"),
    path("new", view=views.YearCreateView.as_view(), name="year-create"),
    path("change", view=views.ChangeYearFormView.as_view(), name="year-change"),
    path("update", view=views.ChangeProductionYearFormView.as_view(), name="year-update"),
]

waiting_slots_patterns = [
    path("add/<int:course_id>", view=views.WaitingSlotCreateView.as_view(), name="waiting_slot-add"),
    path(
        "<int:pk>/transform",
        view=views.WaitingSlotTransformView.as_view(),
        name="waiting_slot-transform",
    ),
    path(
        "<int:pk>/delete",
        view=views.WaitingSlotDeleteView.as_view(),
        name="waiting_slot-delete",
    ),
]

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("activity/", include(activities_patterns)),
    path("allocations/", include(allocations_patterns)),
    path("buildings/", include(buildings_patterns)),
    path("child/", include(children_patterns)),
    path("course/", include(courses_patterns)),
    path("dates", views.RegistrationDatesView.as_view(), name="dates"),
    path("mail/", include(mail_patterns)),
    path("payroll/", include(payroll_patterns)),
    path("registrations/", include(registrations_patterns)),
    path("teacher/", include(teachers_patterns)),
    path("user/", include(users_patterns)),
    path("site/", include(site_patterns)),
    path("year/", include(years_patterns)),
    path("waiting-slots/", include(waiting_slots_patterns)),
]
