import json
import urllib.parse

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, View

import requests
from braces.views import LoginRequiredMixin, UserPassesTestMixin

import mailer.views as mailer_views
from mailer.forms import CourseMailForm, InstructorCopiesForm
from mailer.mixins import ArchivedMailMixin
from registrations.models import Registration
from wizard.views import StaticStepView
from .models import Activity, Course, PaySlip


__all__ = (
    "InstructorMixin",
    "ActivityDetailView",
    "CustomParticipantsCustomMailView",
    "MyCoursesListView",
    "MyCourseDetailView",
    "MailUsersView",
    "CustomMailPreview",
    "MailCourseInstructorsView",
    "PaySlipDetailView",
    "WizardQuestionsStepView",
)


class InstructorMixin(UserPassesTestMixin, LoginRequiredMixin):
    """Mixin for backend. Ensure that the user is logged in and is a sports responsible"""

    pk_url_kwarg = "course"

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Course, pk=pk)

    def test_func(self, user):
        # noinspection PyUnresolvedReferences
        if self.pk_url_kwarg in self.kwargs:
            course = self.get_object()
            return user.is_active and user.is_instructor_of(course)
        return user.is_active and user.is_instructor


class CourseAccessMixin(UserPassesTestMixin, LoginRequiredMixin):
    pk_url_kwarg = "course"

    # noinspection PyUnresolvedReferences
    def get_object(self):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Course, pk=pk)

    def test_func(self, user):
        course = self.get_object()
        return user.is_authenticated and (
            user.is_instructor_of(course) or user in [p.child.family for p in course.participants.all()]
        )


class ActivityDetailView(DetailView):
    model = Activity

    def get_queryset(self):
        prefetched = Activity.objects.prefetch_related("courses", "courses__participants", "courses__instructors")
        return prefetched.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        activity = kwargs["object"]
        if not self.request.user.is_authenticated:
            context["registrations"] = {}
            return context

        registrations = {}
        children = self.request.user.children.all()
        for course in activity.courses.prefetch_related("participants__child"):
            participants = [reg.child for reg in course.participants.all()]
            for child in children:
                if child in participants:
                    registrations[course] = participants
                    break

        context["registrations"] = registrations
        return context


class MyCoursesListView(InstructorMixin, ListView):
    template_name = "activities/course_list.html"

    def get_queryset(self):
        return Course.objects.filter(instructors=self.request.user)


class MyCourseDetailView(CourseAccessMixin, DetailView):
    model = Course
    template_name = "activities/course_detail.html"
    pk_url_kwarg = "course"
    queryset = Course.objects.select_related("activity").prefetch_related(
        "participants__child__school_year", "participants__child__family", "instructors"
    )


class MailUsersView(CourseAccessMixin, View):
    def post(self, request, *args, **kwargs):
        userids = list(set(json.loads(request.POST.get("data", "[]"))))
        self.request.session["mail-userids"] = userids
        params = ""
        if "prev" in request.GET:
            params = "?prev=" + urllib.parse.urlencode(request.GET.get("prev"))
        return HttpResponseRedirect(
            reverse("activities:mail-custom-participants-custom", kwargs={"course": kwargs["course"]}) + params
        )


class CustomMailCreateView(InstructorMixin, mailer_views.ParticipantsMailCreateView):
    template_name = "activities/mail-create.html"
    form_class = CourseMailForm

    def get_success_url(self):
        course = self.kwargs["course"]
        return reverse("activities:mail-preview", kwargs={"course": course})


class CustomMailPreview(InstructorMixin, ArchivedMailMixin, mailer_views.ParticipantsMailPreviewView):
    group_mails = True
    template_name = "activities/mail-preview-editlink.html"
    edit_url = reverse_lazy("activities:mail-participants-custom")

    def get_edit_url(self):
        if not self.course:
            self.course = self.kwargs["course"]
        return self.course.get_custom_mail_instructors_url()

    def get_success_url(self):
        return reverse("activities:course-detail", kwargs=self.kwargs)

    def get_reply_to_address(self):
        return self.request.user.get_email_string()


class CustomParticipantsCustomMailView(InstructorMixin, mailer_views.MailCreateView):
    template_name = "activities/mail-create.html"
    form_class = CourseMailForm

    def get(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        return super().post(*args, **kwargs)

    def get_success_url(self):
        return reverse("activities:mail-preview", kwargs={"course": self.course.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if len(self.get_recipients()) == 1:
            kwargs["enable_copy_all_admins"] = True
        return kwargs


class MailCourseInstructorsView(InstructorMixin, mailer_views.MailCourseInstructorsView):
    template_name = "activities/confirm_send.html"
    form_class = InstructorCopiesForm

    def get_success_url(self):
        return reverse("activities:my-courses")

    def get_recipients(self):
        return [self.request.user]


class PaySlipDetailView(DetailView):
    template_name = "activities/pay-slip-detail.html"
    model = PaySlip

    def get(self, request, *args, **kwargs):
        if self.request.GET.get("pdf", False):
            return self.pdf(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def pdf(self, request, *args, **kwargs):
        """output: filelike object"""
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        content = render_to_string(self.template_name, context=context, request=request)

        phantomjs_conf = {
            "backend": "chrome",
            "content": content,
            "renderType": "pdf",
            "omitBackground": True,
            "renderSettings": {
                "emulateMedia": "print",
                "pdfOptions": {
                    "format": "A4",
                    "landscape": False,
                    "preferCSSPageSize": True,
                },
            },
            "requestSettings": {
                "waitInterval": 0,
                "resourceTimeout": 2000,
                "doneWhen": [{"event": "domReady"}],
            },
        }

        pdf = requests.post(
            f"https://PhantomJsCloud.com/api/browser/v2/{settings.PHANTOMJSCLOUD_APIKEY}/",
            json.dumps(phantomjs_conf),
        )
        if not pdf.status_code == 200:
            raise OSError(pdf.text)
        response = HttpResponse(pdf.content, content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=%s.pdf" % self.object.pk
        return response


class WizardQuestionsStepView(LoginRequiredMixin, StaticStepView):
    template_name = "wizard/questions.html"

    def get_step_slug(self):
        return self.kwargs["step_slug"]

    def get_context_data(self, **kwargs):
        from registrations.forms import ExtraInfoForm
        from registrations.models import ExtraInfo

        context = super().get_context_data(**kwargs)
        questions = self.get_step().questions.all()
        context["questions"] = questions
        questions_registrations = {}
        # Iterate through each ExtraNeed
        context["forms"] = []
        for extra_need in questions:
            # Find all children who are registered in the course related to this ExtraNeed
            registrations = Registration.waiting.filter(
                course__in=extra_need.courses.all(), child__family=self.request.user
            )

            if registrations:
                # Store the registrations (children) for this extra need
                questions_registrations[extra_need] = [registration.child for registration in registrations]
            for registration in registrations:
                # Try to retrieve an existing ExtraInfo object for this registration and extra_need
                answer, _created = ExtraInfo.objects.get_or_create(
                    key=extra_need,
                    registration=registration,
                    defaults={"key": extra_need, "registration": registration},
                )

                # Create a unique form prefix using `extra_need.pk` and `registration.pk`
                form_prefix = f"question-{extra_need.pk}-reg-{registration.pk}"
                form = ExtraInfoForm(prefix=form_prefix, instance=answer)
                context["forms"].append(form)
        context["questions_registrations"] = questions_registrations
        return context
