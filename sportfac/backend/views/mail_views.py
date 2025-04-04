from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import ListView

import mailer.views as mailer_views
from activities.models import Course
from mailer.forms import AdminMailForm
from mailer.mixins import ArchivedMailMixin, ParticipantsMixin, TemplatedEmailMixin
from mailer.models import MailArchive
from mailer.tasks import send_mail
from profiles.models import FamilyUser
from registrations.models import Bill, Registration
from registrations.views.utils import BillMixin
from .mixins import BackendMixin


class MailArchiveListView(BackendMixin, ListView):
    queryset = MailArchive.sent.all()
    template_name = "backend/mail/list.html"


class MailCreateView(BackendMixin, mailer_views.MailCreateView):
    """Send email to a given set of users - form"""

    template_name = "backend/mail/create.html"
    success_url = reverse_lazy("backend:custom-mail-custom-users-preview")
    form_class = AdminMailForm


class MailPreview(BackendMixin, ArchivedMailMixin, mailer_views.MailPreviewView):
    """Send email to a given set of users - preview"""

    success_url = reverse_lazy("backend:user-list")
    template_name = "backend/mail/preview.html"
    edit_url = reverse_lazy("backend:custom-mail-custom-users")

    def get_cancel_url(self):
        return self.request.GET.get("prev", None)


class ParticipantsMailCreateView(BackendMixin, mailer_views.ParticipantsMailCreateView):
    """Send email to all participants of a course - form"""

    template_name = "backend/mail/create.html"

    def get_success_url(self):
        return reverse("backend:mail-participants-custom-preview", kwargs={"course": self.course.pk})


class ParticipantsMailPreview(BackendMixin, ArchivedMailMixin, mailer_views.ParticipantsMailPreviewView):
    """Send email to all participants of a course - preview"""

    template_name = "backend/mail/preview.html"
    group_mails = True

    def get_edit_url(self):
        return reverse("backend:mail-participants-custom", kwargs={"course": self.course.pk})

    def get_success_url(self):
        return reverse("backend:course-detail", kwargs=self.kwargs)


class MailCourseInstructorsView(BackendMixin, mailer_views.MailCourseInstructorsView):
    template_name = "backend/course/confirm_send.html"

    def get_success_url(self):
        return reverse("backend:course-detail", kwargs=self.kwargs)


class MailConfirmationParticipantsView(
    BackendMixin, ParticipantsMixin, TemplatedEmailMixin, mailer_views.BrowsableMailPreviewView
):
    subject_template = "mailer/course_begin_subject.txt"
    message_template = "mailer/course_begin.txt"
    template_name = "backend/mail/preview-browse.html"
    edit_url = None
    group_mails = False
    mail_type = "convocation"

    def get_success_url(self):
        return self.course.backend_url

    def get_cancel_url(self):
        return self.course.backend_url


class MailConfirmationCoursesView(
    BackendMixin, ParticipantsMixin, TemplatedEmailMixin, mailer_views.BrowsableMailPreviewView
):
    subject_template = "mailer/course_begin_subject.txt"
    message_template = "mailer/course_begin.txt"
    template_name = "backend/mail/preview-browse.html"
    edit_url = None
    group_mails = False
    mail_type = "convocation"

    def get_success_message(self):
        return self.success_message % {"number": sum([course.participants.count() for course in self.courses])}

    def get_recipients(self):
        qs = self.course.participants.select_related("child__family")
        all_recipients = [registration.child.family for registration in qs.all()]
        if self.group_mails:
            return list(set(all_recipients))
        return all_recipients

    def get_success_url(self):
        return reverse("backend:course-list")

    def get_cancel_url(self):
        return reverse("backend:course-list")

    def get_context_data(self, **kwargs):
        kwargs["course"] = self.course
        kwargs["courses"] = self.courses
        kwargs["base_url"] = self.request.path + "?" + "&".join([f"c={course.pk}" for course in self.courses])

        # noinspection PyUnresolvedReferences
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        courses_pk = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
        self.courses = Course.objects.filter(pk__in=courses_pk)
        selected_course_pk = self.request.GET.get("selected") or self.courses.first().pk
        self.course = Course.objects.get(pk=selected_course_pk)
        return super(mailer_views.BrowsableMailPreviewView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        courses_pk = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
        self.courses = Course.objects.filter(pk__in=courses_pk)
        for course in self.courses:
            self.course = course
            context = {"course": self.course}
            for registration in course.participants.all():
                self.send_mail(
                    recipient=registration.child.family,
                    bcc_recipients=self.get_bcc_recipients(),
                    base_context=context,
                    child=registration.child,
                )
            self.create_receipt()

        messages.success(request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())

    def send_mail(self, recipient, bcc_recipients, base_context, child=None):
        mail_context = self.get_mail_context(base_context, recipient, bcc_recipients, child)
        message = self.get_mail_body(mail_context)
        send_mail.delay(
            subject=self.get_subject(mail_context),
            message=message,
            from_email=self.get_from_address(),
            recipients=[recipient.get_email_string()],
            reply_to=[self.get_reply_to_address()],
            bcc=[user.get_email_string() for user in bcc_recipients],
            attachments=[attachment.pk for attachment in self.get_attachments(mail_context)],
        )
        return message


class MailInstructorsCoursesView(MailCourseInstructorsView):
    template_name = "backend/course/confirm_send.html"

    def get_context_data(self, **kwargs):
        kwargs["courses"] = self.courses
        kwargs["cancel_url"] = self.get_cancel_url()
        return super().get_context_data(**kwargs)

    def get(self, *args, **kwargs):
        courses_pk = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
        self.courses = Course.objects.filter(pk__in=courses_pk)
        self.course = self.courses.first()
        return self.render_to_response(self.get_context_data())

    def post(self, *args, **kwargs):
        courses_pk = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
        self.courses = Course.objects.filter(pk__in=courses_pk)
        self.course = self.courses.first()

        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def get_recipients(self):
        return self.course.instructors.all()

    def form_valid(self, form):
        bcc_list = self.get_bcc_list(form)
        recipients_nb = 0
        for course in self.courses:
            self.course = course
            if form.cleaned_data.get("copy_all_instructors", False):
                recipients = self.course.instructors.all()
            else:
                recipients = self.get_recipients()
            recipients_nb += len(recipients)
            for instructor in recipients:
                self.send_to_instructor(instructor, bcc_list)
            self.create_receipt()
        messages.success(
            self.request,
            _("Your email is being sent to %(number)s recipients.") % {"number": recipients_nb},
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("backend:course-list")

    def get_cancel_url(self):
        return reverse("backend:course-list")


class NotPaidYetView(BackendMixin, BillMixin, TemplatedEmailMixin, mailer_views.BrowsableMailPreviewView):
    """Mail to people having registered to courses but not paid yet"""

    subject_template = "mailer/notpaid_subject.txt"
    message_template = "mailer/notpaid.txt"
    template_name = "backend/mail/preview-browse.html"
    success_url = reverse_lazy("backend:home")
    mail_type = "not_paid"

    def get_context_data(self, **kwargs):
        kwargs["delay"] = self.global_preferences["payment__DELAY_DAYS"]
        kwargs["iban"] = self.global_preferences["payment__IBAN"]
        kwargs["address"] = self.global_preferences["payment__ADDRESS"]
        kwargs["place"] = self.global_preferences["payment__PLACE"]
        return super().get_context_data(**kwargs)

    def get_recipients(self):
        bills = Bill.objects.filter(status=Bill.STATUS.waiting, total__gt=0, reminder_sent=False)
        return list(FamilyUser.objects.filter(pk__in=[bill.family.pk for bill in bills]))


class NeedConfirmationView(BackendMixin, TemplatedEmailMixin, mailer_views.BrowsableMailPreviewView):
    """Mail to people having not confirmed activities yet."""

    success_url = reverse_lazy("backend:home")
    subject_template = "mailer/need_confirmation_subject.txt"
    message_template = "mailer/need_confirmation.txt"
    template_name = "backend/mail/preview-browse.html"
    mail_type = "need_confirmation"

    def get_recipients(self):
        return list({reg.child.family for reg in Registration.objects.waiting()})

    def get_context_data(self, **kwargs):
        kwargs["url"] = "".join(
            (
                settings.DEBUG and "http://" or "https://",
                get_current_site(self.request).domain,
                reverse("wizard:step", kwargs={"step_slug": "confirmation"}),
            )
        )
        return super().get_context_data(**kwargs)
