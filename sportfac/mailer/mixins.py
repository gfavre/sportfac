# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

import six
from activities.models import Course, TemplatedEmailReceipt
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser

from . import tasks
from .models import MailArchive


class GlobalPreferencesMixin(object):
    def __init__(self, *args, **kwargs):
        self.global_preferences = global_preferences_registry.manager()
        super(GlobalPreferencesMixin, self).__init__(*args, **kwargs)


class BaseEmailMixin(GlobalPreferencesMixin):
    from_address = None
    reply_to_address = None
    recipients = None
    bcc_recipients = None
    subject = None
    mail_body = None
    attachments = None
    success_message = _("Your email is being sent to %(number)s recipients.")

    @staticmethod
    def resolve_template(template):
        """Accepts a template object, path-to-template or list of paths"""
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, six.string_types):
            return loader.get_template(template)
        else:
            return template

    def get_success_message(self):
        return self.success_message % {"number": len(self.get_recipients())}

    def get_mail_context(self, base_context, recipient, bcc_list=None):
        context = base_context.copy()
        if not bcc_list:
            bcc_list = []
        context["recipient"] = recipient
        context["to_email"] = recipient.get_email_string()
        context["bcc"] = bcc_list
        return context

    def get_recipients(self):
        if not self.recipients:
            raise NotImplementedError("Add a recipients attribute")

    def get_bcc_recipients(self):
        if self.bcc_recipients:
            return self.bcc_recipients
        return []

    def get_from_address(self):
        if self.from_address:
            return self.from_address
        return self.global_preferences["email__FROM_MAIL"]

    def get_reply_to_address(self):
        if self.reply_to_address:
            return self.reply_to_address
        return self.global_preferences["email__REPLY_TO_MAIL"]

    def get_recipient_addresses(self):
        return [recipient.get_email_string() for recipient in self.get_recipients()]

    def get_bcc_addresses(self):
        return [recipient.get_email_string() for recipient in self.get_bcc_recipients()]

    def get_subject(self, context):
        if not self.subject:
            raise NotImplementedError("Add a subject attribute")
        return self.subject

    def get_mail_body(self, context):
        if not self.mail_body:
            raise NotImplementedError("Add a mail_body attribute")
        return self.mail_body

    def get_attachments(self, context):
        if not self.attachments:
            return []


class CancelableMixin(object):
    cancel_url = None

    def get_cancel_url(self):
        if self.cancel_url:
            # Forcing possible reverse_lazy evaluation
            return force_str(self.cancel_url)
        return None


class EditableMixin(object):
    edit_url = None

    def get_edit_url(self):
        if self.edit_url:
            # Forcing possible reverse_lazy evaluation
            return force_str(self.edit_url)
        return None


class ArchivedMailMixin(BaseEmailMixin):
    archive = None

    def get_mail_archive(self):
        mail_pk = self.request.session.get("mail", None)
        return get_object_or_404(MailArchive, pk=mail_pk)

    def get(self, request, *args, **kwargs):
        self.archive = self.get_mail_archive()
        return super(ArchivedMailMixin, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.archive = self.get_mail_archive()
        return super(ArchivedMailMixin, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs["mail_archive"] = self.archive
        return super(ArchivedMailMixin, self).get_context_data(**kwargs)

    def get_recipients(self):
        return list(FamilyUser.objects.filter(pk__in=self.archive.recipients))

    def get_bcc_recipients(self):
        return list(FamilyUser.objects.filter(pk__in=self.archive.bcc_recipients))

    def get_subject(self, context):
        return self.archive.subject

    def get_mail_body(self, context):
        template = self.resolve_template(self.archive.template)
        return template.render(context)

    def get_attachments(self, context):
        return self.archive.attachments.all()


class TemplatedEmailMixin(BaseEmailMixin):
    message_template = None
    subject_template = None
    mail_type = None
    course = None

    def create_receipt(self):
        kwargs = {"type": self.get_mail_type()}
        if self.course is not None:
            kwargs["course"] = self.course
        TemplatedEmailReceipt.objects.update_or_create(**kwargs)

    def get_mail_type(self):
        if not self.mail_type:
            raise NotImplementedError("Add a mail_type")
        return self.mail_type

    def get_mail_body(self, context):
        if not self.message_template:
            raise NotImplementedError("Add a message_template")
        template = self.resolve_template(self.message_template)
        return template.render(context)

    def get_subject(self, context):
        if not self.subject_template:
            raise NotImplementedError("Add a subject_template")
        template = self.resolve_template(self.subject_template)
        return template.render(context)


class ParticipantsBaseMixin(object):
    group_mails = False

    def get_recipients(self):
        qs = self.course.participants.select_related("child__family")
        all_recipients = [registration.child.family for registration in qs.all()]
        if self.group_mails:
            return list(set(all_recipients))
        return all_recipients

    def get_context_data(self, **kwargs):
        kwargs["course"] = self.course
        return super(ParticipantsBaseMixin, self).get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        return super(ParticipantsBaseMixin, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        return super(ParticipantsBaseMixin, self).post(request, *args, **kwargs)


class ParticipantsMixin(ParticipantsBaseMixin, BaseEmailMixin):
    def add_nth_mail_context(self, context, nth):
        try:
            context["registration"] = self.course.participants.all()[nth]
            context["child"] = context["registration"].child
        except IndexError:
            pass

    def get_mail_context(self, base_context, recipient, bcc_list=None, child=None):
        base_context = super(ParticipantsMixin, self).get_mail_context(
            base_context, recipient, bcc_list
        )
        if child:
            base_context["registration"] = self.course.participants.get(child=child)
            base_context["child"] = child
        return base_context

    def send_mail(self, recipient, bcc_recipients, base_context, child=None):
        mail_context = self.get_mail_context(base_context, recipient, bcc_recipients, child)
        message = self.get_mail_body(mail_context)
        tasks.send_mail.delay(
            subject=self.get_subject(mail_context),
            message=self.get_mail_body(mail_context),
            from_email=self.get_from_address(),
            recipients=[recipient.get_email_string()],
            reply_to=[self.get_reply_to_address()],
            bcc=[user.get_email_string() for user in bcc_recipients],
            attachments=[attachment.pk for attachment in self.get_attachments(mail_context)],
        )
        if hasattr(self, "create_receipt"):
            self.create_receipt()
        return message

    def get(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        return super(ParticipantsMixin, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs["course"])
        context = self.get_context_data()
        if self.group_mails:
            all_recipients = self.get_recipients() + self.get_bcc_recipients()
            for recipient in all_recipients:
                self.send_mail(recipient, [], context)
        else:
            for registration in self.course.participants.all():
                self.send_mail(
                    recipient=registration.child.family,
                    bcc_recipients=self.get_bcc_recipients(),
                    base_context=context,
                    child=registration.child,
                )

        if "mail" in self.request.session:
            del request.session["mail"]
        if "mail-userids" in self.request.session:
            del request.session["mail-userids"]
        messages.success(request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())
