import itertools
import time

import six

from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponseRedirect
from django.template import loader, Context
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _
from django.views.generic.base import TemplateView, ContextMixin
from django.views.generic.edit import FormView

from dbtemplates.models import Template

from activities.models import Course
from backend.dynamic_preferences_registry import global_preferences_registry
from .forms import MailForm
from .models import MailArchive, Attachment
from .tasks import send_mail, send_instructors_email


class MailMixin(ContextMixin):
    recipients_queryset = None
    success_url = None
    from_email = None
    subject = None
    subject_template = None
    message_template = None
    from_address = None
    reply_to_address = None
    success_message = ''
    attachments = None

    def __init__(self, *args, **kwargs):
        self.global_preferences = global_preferences_registry.manager()
        return super(MailMixin, self).__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(MailMixin, self).get_context_data(**kwargs)
        context['signature'] = self.global_preferences['email__SIGNATURE']
        current_site = get_current_site(self.request)
        context['site_name'] = current_site.name
        context['site_url'] = 'http://%s' % current_site.domain
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
            return self.recipients_queryset.all()

        if self.recipients_queryset:
            return self.recipients_queryset.all()
        return []

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

    def resolve_template(self, template):
        "Accepts a template object, path-to-template or list of paths"
        if isinstance(template, (list, tuple)):
            return loader.select_template(template)
        elif isinstance(template, six.string_types):
            return loader.get_template(template)
        else:
            return template

    def get_subject(self):
        context = self.get_context_data()
        return self.get_subject_template().render(Context(context))

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
            return reply_to_address
        return self.global_preferences['email__REPLY_TO_MAIL']
    

    def get_success_message(self):
        if self.success_message:
            return self.success_message
        return _("Message has been scheduled to be sent.")

    def get_mail_body(self, context):
        return self.get_message_template().render(Context(context))

    def add_recipient_context(self, recipient, context):
        context['recipient'] = recipient

    def mail(self, context):
        recipients = self.get_recipients_list()
        emails = []
        recipients_addresses = []
        subject = self.get_subject()
        from_email = self.get_from_address()
        reply_to = [self.get_reply_to_address()]
        attachments = [fileobj.file.name for fileobj in self.get_attachments()]
        
        if reply_to[0] != from_email:
            reply_to = []
        for recipient in recipients:
            if not recipient:
                continue
            mail_context = context.copy()
            self.add_recipient_context(recipient, mail_context)
            message = self.get_mail_body(mail_context)
            recipient_address = self.get_recipient_address(recipient)
            
            send_mail.delay(subject=subject,
                            message=message,
                            from_email=from_email,
                            recipients=[recipient_address, ],
                            reply_to=reply_to,
                            attachments=attachments)
            emails.append(message)
            recipients_addresses.append(recipient_address)
        MailArchive.objects.create(subject=subject, messages=emails,
                                   recipients=recipients_addresses,
                                   template=self.get_message_template())

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        self.mail(context)
        messages.add_message(self.request, messages.SUCCESS,
                             self.get_success_message())
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

        context['url'] = ''.join(('http://',
                                  get_current_site(self.request).domain,
                                  reverse('wizard_confirm')))
        return context

    def get_success_url(self):
        return self.course.get_backend_url()


class MailCourseInstructorsView(MailMixin, CourseMixin, TemplateView):
    message_template = 'mailer/instructor.txt'
    subject_template = 'mailer/instructor_subject.txt'

    def get_recipients_list(self):
        return self.course.instructors.all()

    def mail(self, context):
        recipients = self.get_recipients_list()
        subject = self.get_subject()
        from_email = self.get_from_address()
        reply_to = [self.get_reply_to_address()]
        if reply_to[0] != from_email:
            reply_to = []
        for recipient in recipients:
            message = self.get_mail_body(context)
            send_instructors_email.delay(subject=subject,
                                         message=message,
                                         from_email=from_email,
                                         course_pk=self.course.pk,
                                         reply_to=reply_to)


class MailView(MailMixin, TemplateView):
    template_name = 'backend/mail/preview.html'

    def add_navigation_context(self, mailnumber, mails, context):
        context['total'] = len(mails)
        context['mailidentifier'] = mailnumber + 1
        context['has_prev'] = mailnumber != 0
        context['prev'] = mailnumber
        context['has_next'] = mailnumber + 1 != context['total']
        context['next'] = mailnumber + 2

    def add_mail_context(self, mailnumber, context):
        "Get context, add navigation"
        context['to_email'] = self.get_recipient_address(context['recipient'])
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments()

    def get(self, request, *args, **kwargs):
        "Preview emails."
        mailnumber = int(self.request.GET.get('number', 1)) - 1
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
        "Get context, add navigation"
        context['to_email'] = self.get_recipient_address(context['registration'])
        context['from_email'] = self.get_from_address()
        context['subject'] = self.get_subject()
        context['message'] = self.get_mail_body(context)
        context['attachments'] = self.get_attachments()
    
    def get_recipient_address(self, recipient):
        return super(MailParticipantsView, self).get_recipient_address(recipient.child.family)

    def get_recipients_list(self):
        return self.course.participants.all()


class MailCreateView(FormView):
    form_class = MailForm

    def get_archive_from_session(self):
        if not 'mail' in self.request.session:
            return None
        try:
            return MailArchive.objects.get(id=self.request.session['mail'])
        except MailArchive.DoesNotExist:
            del self.request.session['mail']
            return None

    def get_template_from_archive(self, archive):
        template, created = Template.objects.get_or_create(
            name=archive.template)
        return template

    def get_initial(self):
        if not 'mail' in self.request.session:
            return {}
        try:
            archive = MailArchive.objects.get(id=self.request.session['mail'])
            template = Template.objects.get(name=archive.template)
            return {'message': template.content,
                    'subject': archive.subject}
        except Template.DoesNotExist:
            return {'subject': archive.subject}
        except MailArchive.DoesNotExist:
            return {}

    def form_valid(self, form):
        archive = self.get_archive_from_session()
        if archive:
            template = self.get_template_from_archive(archive)
            archive.subject = form.cleaned_data['subject']
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
                recipients=[],
                messages=[],
                template=template.name)
            self.request.session['mail'] = archive.id
        for attachment in form.cleaned_data['attachments']:
            Attachment.objects.create(file=attachment, mail=archive)
        
        template.content = form.cleaned_data['message']
        template.save()
        return super(MailCreateView, self).form_valid(form)


class CustomMailMixin(object):
    
    def get_attachments(self):
        mail_id = self.request.session.get('mail', None)
        attachments = []
        try:
            mail = MailArchive.objects.get(id=mail_id)
            attachments = [attachment.file for attachment in mail.attachments.all()]
        except MailArchive.DoesNotExist:
            raise Http404()
        return attachments

    
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


