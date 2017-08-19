# -*- coding: utf-8 -*-
import itertools
import time
import six

from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404
from django.http import HttpResponseRedirect
from django.template import loader
from django.template.defaultfilters import urlencode
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, ContextMixin
from django.views.generic.edit import FormView

from dbtemplates.models import Template

from activities.models import Course
from backend.dynamic_preferences_registry import global_preferences_registry
from profiles.models import FamilyUser
from .forms import MailForm, CopiesForm, CourseMailForm
from .models import MailArchive, Attachment
from .mixins import (CancelableMixin, EditableMixin, ArchivedMailMixin, TemplatedEmailMixin,
                     ParticipantsBaseMixin, ParticipantsMixin)
from .tasks import send_mail, send_instructors_email


class MailMixin(ContextMixin):
    recipients_queryset = None
    bcc_list = None
    success_url = None
    from_email = None
    subject = None
    subject_template = None
    message_template = None
    from_address = None
    reply_to_address = None
    success_message = ''
    attachments = None

    form_class = None

    def __init__(self, *args, **kwargs):
        self.global_preferences = global_preferences_registry.manager()
        super(MailMixin, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MailMixin, self).get_context_data(**kwargs)
        context['signature'] = self.global_preferences['email__SIGNATURE']
        current_site = get_current_site(self.request)
        context['site_name'] = current_site.name
        context['site_url'] = settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain
        context['bcc'] = self.get_bcc_list()
        return context
    
    def get_attachments(self):
        if self.attachments is None:
            return []
        return self.attachments
    
    def get_recipients_list(self):
        if self.recipients_queryset is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'recipients_queryset' or an implementation of 'get_subject_template'")
        else:
            if self.recipients_queryset:
                return self.recipients_queryset.all()
        return []

    def get_bcc_list(self):
        if self.bcc_list is None:
            return []
        return self.bcc_list

    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def get_recipient_address(self, recipient):
        if not recipient:
            return ''
        to = '%s %s <%s>'
        return to % (recipient.first_name,
                     recipient.last_name, recipient.email)

    @staticmethod
    def resolve_template(template):
        """Accepts a template object, path-to-template or list of paths"""
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, six.string_types):
            return loader.get_template(template)
        else:
            return template

    def get_subject(self):
        context = self.get_context_data()
        return self.get_subject_template().render(context)

    def get_subject_template(self):
        if self.subject_template is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'subject' or an implementation of 'get_subject'")
        return self.resolve_template(self.subject_template)

    def get_message_template(self):
        if self.message_template is None:
            raise ImproperlyConfigured(
                "MailMixin requires either a definition of "
                "'message_template' or an implementation of 'get_subject_template'")
        else:
            return self.resolve_template(self.message_template)

    def get_from_address(self):
        if self.from_address:
            return self.from_address
        return self.global_preferences['email__FROM_MAIL']
    
    def get_reply_to_address(self):
        if self.reply_to_address:
            return self.reply_to_address
        return self.global_preferences['email__REPLY_TO_MAIL']

    def get_success_message(self):
        if self.success_message:
            return self.success_message
        return _("Message has been scheduled to be sent.")

    def get_mail_body(self, context):
        return self.get_message_template().render(context)

    def add_recipient_context(self, recipient, context):
        context['recipient'] = recipient

    def send_mail(self, recipient, base_context, attachments):
        mail_context = base_context.copy()
        self.add_recipient_context(recipient, mail_context)
        message = self.get_mail_body(mail_context)
        send_mail.delay(subject=self.get_subject(),
                        message=self.get_mail_body(mail_context),
                        from_email=self.get_from_address(),
                        recipients=[self.get_recipient_address(recipient)],
                        reply_to=[self.get_reply_to_address()],
                        attachments=attachments)
        return message

    def mail(self, context):
        emails = []
        recipients_addresses = []
        bcc_addresses = []

        attachments = [fileobj.file.name for fileobj in self.get_attachments()]

        for recipient in self.get_recipients_list():
            if not recipient:
                continue
            message = self.send_mail(recipient, context, attachments)
            emails.append(message)
            recipients_addresses.append(self.get_recipient_address(recipient))

        for bcc_recipient in self.get_bcc_list():
            message = self.send_mail(bcc_recipient, context, attachments)
            emails.append(message)
            bcc_addresses.append(self.get_recipient_address(bcc_recipient))

        MailArchive.objects.create(subject=subject, messages=emails,
                                   recipients=recipients_addresses,
                                   bcc_recipients=bcc_addresses,
                                   template=self.get_message_template())

    def form_valid(self, form):
        context = self.get_context_data(**self.kwargs)
        self.mail(context)
        messages.add_message(self.request, messages.SUCCESS, self.get_success_message())
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)

    def post(self, request, *args, **kwargs):
        if self.form_class:
            form = self.form_class(data=self.request.POST, files=self.request.FILES)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)

        context = self.get_context_data(**kwargs)
        self.mail(context)
        messages.add_message(self.request, messages.SUCCESS, self.get_success_message())
        success_url = self.get_success_url()
        return HttpResponseRedirect(success_url)


class CourseMixin(object):

    def get_context_data(self, **kwargs):
        context = super(CourseMixin, self).get_context_data(**kwargs)
        try:
            course = Course.objects.get(pk=self.kwargs.get('course'))
            self.course = course
            context['course'] = course
        except Course.DoesNotExist:
            raise Http404(_("No course found"))

        context['url'] = ''.join((settings.DEBUG and 'http://' or 'https://',
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context

    def get_success_url(self):
        return self.course.get_backend_url()





class MailView(MailMixin, TemplateView):
    template_name = 'backend/mail/preview.html'

    @staticmethod
    def add_navigation_context(mailnumber, mails, context):
        context['total'] = len(mails)
        context['mailidentifier'] = mailnumber + 1
        context['has_prev'] = mailnumber != 0
        context['prev'] = mailnumber
        context['has_next'] = mailnumber + 1 != context['total']
        context['next'] = mailnumber + 2

    def add_mail_context(self, mailnumber, context):
        """Get context, add navigation"""
        context['to_email'] = self.get_recipient_address(context['recipient'])
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments()

    def get(self, request, *args, **kwargs):
        """Preview emails."""
        mailnumber = int(self.request.GET.get('number', 1)) - 1
        if self.request.GET.get('new', False) and 'mail-userids' in self.request.session:
            del self.request.session['mail-userids']
        context = self.get_context_data(**kwargs)
        recipients = self.get_recipients_list()
           
        self.add_navigation_context(mailnumber, recipients, context)
        
        try:
            self.add_recipient_context(recipients[mailnumber], context)
        except IndexError:
            raise Http404(_("No recipient found"))
        self.add_mail_context(mailnumber, context)
        return self.render_to_response(context)


class MailParticipantsView(CourseMixin, MailView):

    def add_recipient_context(self, recipient, context):
        context['recipient'] = recipient.child.family
        context['child'] = recipient.child
        context['registration'] = recipient

    def add_mail_context(self, mailnumber, context):
        """Get context, add navigation"""
        context['to_email'] = self.get_recipient_address(context['registration'])
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments()

    def get_context_data(self, **kwargs):
        context = super(MailParticipantsView, self).get_context_data()
        context['bcc'] = self.get_bcc_list()
        return context

    def get_recipient_address(self, recipient):
        return super(MailParticipantsView, self).get_recipient_address(recipient.child.family)

    def get_recipients_list(self):
        qs = self.course.participants.all()
        if 'mail-userids' in self.request.session:
            qs = qs.filter(child__family__in=self.request.session['mail-userids'])
        return qs

    def get_bcc_list(self):
        if 'mail' not in self.request.session:
            return []
        try:
            bcc_pks = MailArchive.objects.get(id=self.request.session['mail']).bcc_recipients
            return FamilyUser.objects.filter(pk__in=bcc_pks)
        except MailArchive.DoesNotExist:
            del self.request.session['mail']
            return []


class CustomMailMixin(object):

    def get_attachments(self):
        mail_id = self.request.session.get('mail', None)
        try:
            mail = MailArchive.objects.get(id=mail_id)
            attachments = [attachment.file for attachment in mail.attachments.all()]
            return attachments
        except MailArchive.DoesNotExist:
            raise Http404()

    def get_subject(self):
        mail_id = self.request.session.get('mail', None)
        try:
            mail = MailArchive.objects.get(id=mail_id)
        except MailArchive.DoesNotExist:
            raise Http404()
        return mail.subject

    def get_message_template(self):
        mail_id = self.request.session.get('mail', None)
        try:
            mail = MailArchive.objects.get(id=mail_id)
        except MailArchive.DoesNotExist:
            raise Http404()
        return self.resolve_template(mail.template)

###################################################################################################


class MailCreateView(FormView):
    """Create mail
    GET params: prev - url
    """
    form_class = MailForm
    success_url = None

    def get_success_url(self):
        if not self.success_url:
            raise NotImplementedError('Add a success_url')
        params = ''
        if 'prev' in self.request.GET:
            params = '?prev=' + urlencode(self.request.GET.get('prev'))
        return self.success_url + params

    @staticmethod
    def get_template_from_archive(archive):
        template, created = Template.objects.get_or_create(name=archive.template)
        return template

    def get_recipients(self):
        user_ids = self.request.session.get('mail-userids', [])
        return [user.pk for user in FamilyUser.objects.filter(pk__in=user_ids)]

    def get_recipients_email(self):
        return [user.get_email_string() for user in FamilyUser.objects.filter(pk__in=self.get_recipients())]

    def get_bcc_from_form(self, form):
        bcc_recipients = set()
        if form.cleaned_data.get('send_copy', False):
            bcc_recipients.add(self.request.user.pk)
        if form.cleaned_data.get('copy_all_admins', False):
            for admin in FamilyUser.managers_objects.all():
                bcc_recipients.add(admin.pk)
        if form.cleaned_data.get('copy_all_instructors', False) and self.course:
            for instructor in self.course.instructors.all():
                bcc_recipients.add(instructor.pk)
        return list(bcc_recipients)

    def get_archive_from_session(self):
        if 'mail' not in self.request.session:
            return None
        try:
            return MailArchive.objects.get(id=self.request.session['mail'])
        except MailArchive.DoesNotExist:
            del self.request.session['mail']
            return None

    def get_initial(self):
        archive = self.get_archive_from_session()
        if archive:
            initial = {'subject': archive.subject,
                       'attachments': archive.attachments.all()}
            try:
                template = Template.objects.get(name=archive.template)
                initial['message'] = template.content
            except Template.DoesNotExist:
                pass
            return initial
        return {}

    def get_context_data(self, **kwargs):
        kwargs['prev'] = self.request.GET.get('prev', None)
        kwargs['archive'] = self.get_archive_from_session()
        kwargs['recipients'] = self.get_recipients_email()
        return super(MailCreateView, self).get_context_data(**kwargs)

    @transaction.atomic
    def form_valid(self, form):
        archive = self.get_archive_from_session()
        if archive:
            template = self.get_template_from_archive(archive)
            archive.subject = form.cleaned_data['subject']
            archive.recipients = self.get_recipients()
            archive.bcc_recipients = self.get_bcc_from_form(form)
            archive.save()
        else:
            template = Template()
            orig = time.strftime('%Y-%m-%d-%H-%M-custom')
            template.name = orig + '.txt'
            for x in itertools.count(1):
                if not Template.objects.filter(name=template.name).exists():
                    break
                template.name = '%s-%d.txt' % (orig, x)

            archive = MailArchive.objects.create(
                status=MailArchive.STATUS.draft,
                subject=form.cleaned_data['subject'],
                recipients=self.get_recipients(),
                bcc_recipients=self.get_bcc_from_form(form),
                messages=[],
                template=template.name,
            )

        for attachment in form.cleaned_data['attachments']:
            Attachment.objects.create(file=attachment, mail=archive)

        template.content = form.cleaned_data['message']
        template.save()
        self.request.session['mail'] = archive.id

        return super(MailCreateView, self).form_valid(form)





class MailPreviewView(CancelableMixin, EditableMixin, TemplateView):
    success_url = None
    template_name = 'mailer/preview.html'

    def get_mail_body(self, context):
        raise NotImplementedError('Either inherit from ArchivedMailMixin or TemplatedMailMixin')

    def get_subject(self, context):
        raise NotImplementedError('Either inherit from ArchivedMailMixin or TemplatedMailMixin')

    def get_success_url(self):
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured("No URL to redirect to. Provide a success_url.")
        return url

    def add_mail_context(self, context):
        context['subject'] = self.get_subject(context)
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments(context)
        context['from_email'] = self.get_from_address()
        context['to_email'] = self.get_recipient_addresses()
        context['bcc_email'] = self.get_bcc_addresses()

    def get_context_data(self, **kwargs):
        current_site = get_current_site(self.request)
        kwargs['site_name'] = current_site.name
        kwargs['site_url'] = settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain
        kwargs['signature'] = self.global_preferences['email__SIGNATURE']
        kwargs['edit_url'] = self.get_edit_url()
        kwargs['cancel_url'] = self.get_cancel_url()
        self.add_mail_context(kwargs)
        return super(MailPreviewView, self).get_context_data(**kwargs)

    def send_mail(self, recipient, bcc_recipients, base_context):
        mail_context = self.get_mail_context(base_context, recipient, bcc_recipients)
        message = self.get_mail_body(mail_context)
        send_mail.delay(
            subject=self.get_subject(mail_context),
            message=self.get_mail_body(mail_context),
            from_email=self.get_from_address(),
            recipients=[recipient.get_email_string()],
            reply_to=[self.get_reply_to_address()],
            bcc=[user.get_email_string() for user in bcc_recipients],
            attachments=[attachment.pk for attachment in self.get_attachments(mail_context)]
        )
        return message

    def post(self, *args, **kwargs):
        all_recipients = self.get_recipients() + self.get_bcc_recipients()
        for recipient in all_recipients:
            context = self.get_context_data()
            self.send_mail(recipient, self.get_bcc_recipients(), context)
        if 'mail' in self.request.session:
            del self.request.session['mail']
        if 'mail-userids' in self.request.session:
            del self.request.session['mail-userids']
        messages.success(self.request, self.get_success_message())
        return HttpResponseRedirect(self.get_success_url())


class BrowsableMailPreviewView(MailPreviewView):
    """MailPreview that offers rendering of individual mails"""
    template_name = 'mailer/browsable-preview.html'

    def add_nth_mail_context(self, context, nth):
        pass

    def add_mail_context(self, context):
        recipient = self.get_recipients()[context['mail_number']]
        context['recipient'] = recipient
        context['to_email'] = [recipient.get_email_string()]
        context['bcc'] = []
        context['from_email'] = self.get_from_address()
        context['bcc_email'] = self.get_bcc_addresses()
        context['subject'] = self.get_subject(context)
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments(context)

    def get_context_data(self, **kwargs):
        mail_number = int(self.request.GET.get('number', 1)) - 1
        kwargs['mail_number'] = mail_number
        kwargs['mailidentifier'] = mail_number + 1
        kwargs['total'] = len(self.get_recipients())
        kwargs['has_prev'] = mail_number != 0
        kwargs['prev'] = mail_number
        kwargs['has_next'] = mail_number + 1 != kwargs['total']
        kwargs['next'] = mail_number + 2
        self.add_nth_mail_context(kwargs, mail_number)
        self.add_mail_context(kwargs)
        return super(BrowsableMailPreviewView, self).get_context_data(**kwargs)


class ParticipantsMailCreateView(ParticipantsBaseMixin, MailCreateView):
    form_class = CourseMailForm


class ParticipantsMailPreviewView(ParticipantsMixin, MailPreviewView):
    def get_edit_url(self):
        return self.course.get_custom_mail_url()

    def get_context_data(self, **kwargs):
        kwargs['prev'] = self.request.GET.get('prev', None)
        return super(ParticipantsMailPreviewView, self).get_context_data(**kwargs)


class MailCourseInstructorsView(ParticipantsMixin, TemplatedEmailMixin, CancelableMixin, FormView):
    form_class = CopiesForm

    message_template = 'mailer/instructor.txt'
    subject_template = 'mailer/instructor_subject.txt'
    form_class = CopiesForm

    def get_recipients(self):
        return self.course.instructors.all()

    def get_instructor_context(self, recipient, bcc_list=None):
        if not bcc_list:
            bcc_list = []
        current_site = get_current_site(self.request)
        return {
            'site_name': current_site.name,
            'site_url': settings.DEBUG and 'http://' + current_site.domain or 'https://' + current_site.domain,
            'signature': self.global_preferences['email__SIGNATURE'],
            'from_email': self.get_from_address(),
            'to_email': recipient.get_email_string(),
            'bcc_email': [bcc_user.get_email_string() for bcc_user in bcc_list],
            'recipient': recipient,
            'course': self.course
        }

    def form_valid(self, form):
        bcc_list = []
        if form.cleaned_data['send_copy']:
            bcc_list = [self.request.user]
        if form.cleaned_data['copy_all_admins']:
            bcc_list += list(FamilyUser.managers_objects.exclude(pk=self.request.user.pk))

        for instructor in self.get_recipients():
            context = self.get_instructor_context(instructor, bcc_list)
            send_instructors_email.delay(
                course_pk=self.course.pk,
                instructor_pk=instructor.pk,
                subject=self.get_subject(context),
                message=self.get_mail_body(context),
                from_email=self.get_from_address(),
                reply_to=[self.get_reply_to_address()],
                bcc=[bcc_user.get_email_string() for bcc_user in bcc_list]
            )
        messages.success(self.request,
                         _('Your email is being sent to %(number)s recipients.') % {
                             'number': len(self.get_recipients())
                         })
        return super(MailCourseInstructorsView, self).form_valid(form)
