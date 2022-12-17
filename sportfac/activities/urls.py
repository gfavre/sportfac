from django.contrib.sitemaps import GenericSitemap
from django.urls import path

from absences.views import AbsenceCourseView

from . import views
from .models import Activity


app_name = "activities"


urlpatterns = [
    path("<int:pk>/", view=views.ActivityDetailView.as_view()),
    path("<slug:slug>/", view=views.ActivityDetailView.as_view(), name="activity-detail"),
    path("my-courses", view=views.MyCoursesListView.as_view(), name="my-courses"),
    path(
        "courses/<int:course>/",
        view=views.MyCourseDetailView.as_view(),
        name="course-detail",
    ),
    path(
        "courses/<int:course>/mail",
        view=views.CustomMailCreateView.as_view(),
        name="mail-participants-custom",
    ),
    path(
        "courses/<int:course>/mail/select",
        view=views.MailUsersView.as_view(),
        name="select-participants",
    ),
    path(
        "courses/<int:course>/mail/custom",
        view=views.CustomParticipantsCustomMailView.as_view(),
        name="mail-custom-participants-custom",
    ),
    path(
        "courses/<int:course>/send-infos",
        view=views.MailCourseInstructorsView.as_view(),
        name="mail-instructors",
    ),
    path(
        "courses/<int:course>/mail/preview",
        view=views.CustomMailPreview.as_view(),
        name="mail-preview",
    ),
    path(
        "courses/<int:course>/absences/",
        view=AbsenceCourseView.as_view(),
        name="course-absence",
    ),
    path(
        "pay-slips/<uuid:pk>/",
        view=views.PaySlipDetailView.as_view(),
        name="payslip-detail",
    ),
]

sitemap = GenericSitemap({"queryset": Activity.objects.all()})
