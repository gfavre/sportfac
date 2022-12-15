import itertools
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.defaultfilters import urlencode
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView

from dbtemplates.models import Template
from profiles.models import FamilyUser

from . import tasks
from .forms import CopiesForm, CourseMailForm, MailForm
from .mixins import (CancelableMixin, EditableMixin, ParticipantsBaseMixin, ParticipantsMixin,
                     TemplatedEmailMixin)
from .models import Attachment, MailArchive


class MailCreateView(FormView):
    """Create mail
    GET params: prev - url
    """

    form_class = MailForm
    success_url = None

    def get_success_url(self):
        if not self.success_url:
            raise NotImplementedError("Add a success_url")
        params = ""
        if "prev" in self.request.GET:
            params = "?prev=" + urlencode(self.request.GET.get("prev"))
        return self.success_url + params

    @staticmethod
    def get_template_from_archive(archive):
        template, created = Template.objects.get_or_create(name=archive.template)
        return template

    def get_recipients(self):
        user_ids = self.request.session.get("mail-userids", [])
        return list(FamilyUser.objects.filter(pk__in=user_ids))

    def get_recipients_email(self):
        return [user.get_email_string() for user in self.get_recipients()]

    def get_bcc_from_form(self, form):
        bcc_recipients = set()
        if form.cleaned_data.get("send_copy", False):
            bcc_recipients.add(str(self.request.user.pk))
        if form.cleaned_data.get("copy_all_admins", False):
            for admin in FamilyUser.managers_objects.all():
                bcc_recipients.add(str(admin.pk))
        if form.cleaned_data.get("copy_all_instructors", False) and self.course:
            for instructor in self.course.instructors.all():
                bcc_recipients.add(str(instructor.pk))
        return list(bcc_recipients)

    def get_archive_from_session(self):
        if "mail" not in self.request.session:
            return None
        try:
            return MailArchive.objects.get(id=self.request.session["mail"])
        except MailArchive.DoesNotExist:
            del self.request.session["mail"]
            return None

    def get_initial(self):
        archive = self.get_archive_from_session()
        if archive:
            initial = {"subject": archive.subject, "attachments": archive.attachments.all()}
            try:
                template = Template.objects.get(name=archive.template)
                initial["message"] = template.content
            except Template.DoesNotExist:
                pass
            return initial
        return {}

    def get_context_data(self, **kwargs):
        kwargs["prev"] = self.request.GET.get("prev", None)
        kwargs["archive"] = self.get_archive_from_session()
        kwargs["recipients"] = self.get_recipients_email()
        return super(MailCreateView, self).get_context_data(**kwargs)

    @transaction.atomic
    def form_valid(self, form):
        archive = self.get_archive_from_session()
        if archive:
            template = self.get_template_from_archive(archive)
            archive.subject = form.cleaned_data["subject"]
            archive.recipients = [str(recipient.pk) for recipient in self.get_recipients()]
            archive.bcc_recipients = self.get_bcc_from_form(form)
            archive.save()
        else:
            template = Template()
            orig = time.strftime("%Y-%m-%d-%H-%M-custom")
            template.name = orig + ".txt"
            for x in itertools.count(1):
                if not Template.objects.filter(name=template.name).exists():
                    break
                template.name = "%s-%d.txt" % (orig, x)

            archive = MailArchive.objects.create(
                status=MailArchive.STATUS.draft,
                subject=form.cleaned_data["subject"],
                recipients=[str(recipient.pk) for recipient in self.get_recipients()],
                bcc_recipients=self.get_bcc_from_form(form),
                messages=[],
                template=template.name,
            )

        for attachment in form.cleaned_data["attachments"]:
            Attachment.objects.create(file=attachment, mail=archive)

        template.content = form.cleaned_data["message"]
        template.save()
        self.request.session["mail"] = archive.id

        return super(MailCreateView, self).form_valid(form)


class MailPreviewView(CancelableMixin, EditableMixin, TemplateView):
    success_url = None
    template_name = "mailer/preview.html"

    def get_mail_body(self, context):
        raise NotImplementedError("Either inherit from ArchivedMailMixin or TemplatedMailMixin")

    def get_subject(self, context):
        raise NotImplementedError("Either inherit from ArchivedMailMixin or TemplatedMailMixin")

    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_str(self.success_url)
        else:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return url

    def add_mail_context(self, context):
        context["subject"] = self.get_subject(context)
        context["message"] = self.get_mail_body(context)
        context["attachments"] = self.get_attachments(context)
        context["from_email"] = self.get_from_address()
        context["to_email"] = self.get_recipient_addresses()
        context["bcc_email"] = self.get_bcc_addresses()

    def get_context_data(self, **kwargs):
        current_site = get_current_site(self.request)
        kwargs["site_name"] = current_site.name
        kwargs["site_url"] = (
            settings.DEBUG and "http://" + current_site.domain or "https://" + current_site.domain
        )
        kwargs["signature"] = self.global_preferences["email__SIGNATURE"]
        kwargs["edit_url"] = self.get_edit_url()
        kwargs["cancel_url"] = self.get_cancel_url()
        if self.get_recipients():
            self.add_mail_context(kwargs)
        return super(MailPreviewView, self).get_context_data(**kwargs)

    def send_mail(self, recipient, bcc_recipients, base_context):
        mail_context = self.get_mail_context(base_context, recipient, bcc_recipients)
        message = self.get_mail_body(mail_context)
        tasks.send_mail.delay(
            subject=self.get_subject(mail_context),
            message=self.get_mail_body(mail_context),
            from_email=self.get_from_address(),
            recipients=[recipient.get_email_string()],
            reply_to=[self.get_reply_to_address()],
            bcc=[user.get_email_string() for user in bcc_recipients],
            attachments=[attachment.pk for attachment in self.get_attachments(mail_context)],
            update_bills=True,
            recipient_pk=str(recipient.pk),
        )
        if hasattr(self, "create_receipt"):
            self.create_receipt()
        return message

    def post(self, *args, **kwargs):
        all_recipients = self.get_recipients() + self.get_bcc_recipients()
        for recipient in all_recipients:
            context = self.get_context_data()
            self.send_mail(recipient, [], context)
        if "mail" in self.request.session:
            del self.request.session["mail"]
        if "mail-userids" in self.request.session:
            del self.request.session["mail-userids"]
        messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())


class BrowsableMailPreviewView(MailPreviewView):
    """MailPreview that offers rendering of individual mails"""

    template_name = "mailer/browsable-preview.html"

    def add_nth_mail_context(self, context, nth):
        pass

    def add_mail_context(self, context):
        recipient = self.get_recipients()[context["mail_number"]]
        context["recipient"] = recipient
        context["to_email"] = [recipient.get_email_string()]
        context["bcc"] = []
        context["from_email"] = self.get_from_address()
        context["bcc_email"] = self.get_bcc_addresses()
        context["subject"] = self.get_subject(context)
        context["message"] = self.get_mail_body(context)
        context["attachments"] = self.get_attachments(context)

    def get_context_data(self, **kwargs):
        mail_number = int(self.request.GET.get("number", 1)) - 1
        kwargs["mail_number"] = mail_number
        kwargs["mailidentifier"] = mail_number + 1
        kwargs["total"] = len(self.get_recipients())
        kwargs["has_prev"] = mail_number != 0
        kwargs["prev"] = mail_number
        kwargs["has_next"] = mail_number + 1 != kwargs["total"]
        kwargs["next"] = mail_number + 2
        self.add_nth_mail_context(kwargs, mail_number)
        return super(BrowsableMailPreviewView, self).get_context_data(**kwargs)


class ParticipantsMailCreateView(ParticipantsBaseMixin, MailCreateView):
    form_class = CourseMailForm


class ParticipantsMailPreviewView(ParticipantsMixin, MailPreviewView):
    def get_edit_url(self):
        return self.course.get_custom_mail_url()

    def get_context_data(self, **kwargs):
        kwargs["prev"] = self.request.GET.get("prev", None)
        return super(ParticipantsMailPreviewView, self).get_context_data(**kwargs)


class MailCourseInstructorsView(
    ParticipantsBaseMixin, TemplatedEmailMixin, CancelableMixin, FormView
):
    form_class = CopiesForm

    message_template = "mailer/instructor.txt"
    subject_template = "mailer/instructor_subject.txt"
    mail_type = "instructors"

    def get_recipients(self):
        return self.course.instructors.all()

    def get_instructor_context(self, recipient, bcc_list=None):
        if not bcc_list:
            bcc_list = []
        current_site = get_current_site(self.request)
        return {
            "site_name": current_site.name,
            "site_url": settings.DEBUG
            and "http://" + current_site.domain
            or "https://" + current_site.domain,
            "signature": self.global_preferences["email__SIGNATURE"],
            "from_email": self.get_from_address(),
            "to_email": recipient.get_email_string(),
            "bcc_email": [bcc_user.get_email_string() for bcc_user in bcc_list],
            "recipient": recipient,
            "course": self.course,
        }

    def form_valid(self, form):
        bcc_list = set()
        if form.cleaned_data.get("send_copy", False):
            bcc_list.add(self.request.user)
        if form.cleaned_data.get("copy_all_admins", False):
            for manager in FamilyUser.managers_objects.exclude(pk=str(self.request.user.pk)):
                bcc_list.add(manager)
        if form.cleaned_data.get("copy_all_instructors", False):
            recipients = self.course.instructors.all()
        else:
            recipients = self.get_recipients()

        for instructor in recipients:
            context = self.get_instructor_context(instructor, bcc_list)
            tasks.send_instructors_email.delay(
                course_pk=self.course.pk,
                instructor_pk=str(instructor.pk),
                subject=self.get_subject(context),
                message=self.get_mail_body(context),
                from_email=self.get_from_address(),
                reply_to=[self.get_reply_to_address()],
                bcc=[bcc_user.get_email_string() for bcc_user in bcc_list],
            )
        self.create_receipt()
        messages.success(
            self.request,
            _("Your email is being sent to %(number)s recipients.")
            % {"number": len(self.get_recipients())},
        )
        return super(MailCourseInstructorsView, self).form_valid(form)
