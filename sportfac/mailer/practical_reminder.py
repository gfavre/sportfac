from django.conf import settings
from django.contrib import messages
from django.db import connection
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import Context
from django.template import Template
from django.templatetags.static import static
from django.utils import timezone
from django.views import View

from backend.dynamic_preferences_registry import global_preferences_registry
from backend.views.mixins import FullBackendMixin
from registrations.models import Registration

from .html import clean_email_html
from .models import GenericEmail
from .models import MailArchive
from .tasks import send_practical_reminder


SUBJECT_TEMPLATE = "mailer/practical_reminder_subject.txt"
BODY_TEMPLATE = "mailer/practical_reminder.html"


class PracticalReminderView(FullBackendMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not settings.KEPCHUP_PRACTICAL_REMINDER:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def registrations(self, request):
        ids = [value for value in request.GET.getlist("c") if value.isdigit()]
        return (
            Registration.objects.filter(course_id__in=ids, child__family__isnull=False)
            .select_related("course", "child__family", "transport")
            .order_by("course__number", "child__last_name", "child__first_name")
        )

    def mail_type(self):
        return (
            GenericEmail.objects.select_related("subject_template", "body_template")
            .filter(body_template__name=BODY_TEMPLATE)
            .first()
        )

    def mail_content(self, request, mail_type, registration):
        context = Context(
            {
                "child": registration.child,
                "course": registration.course,
                "registration": registration,
                "year": timezone.localdate().year,
                "logo_url": request.build_absolute_uri(static("img/logo.png")),
            }
        )
        subject = Template(mail_type.subject_template.content).render(context).strip()
        body = Template(mail_type.body_template.content).render(context)
        return subject, clean_email_html(body) if mail_type.is_html else body

    def get(self, request):
        registrations = self.registrations(request)
        mail_type = self.mail_type()
        total = registrations.count()
        try:
            number = max(1, min(int(request.GET.get("number", 1)), total))
        except ValueError:
            number = 1
        registration = registrations[number - 1] if total else None
        subject, body = self.mail_content(request, mail_type, registration) if mail_type and registration else ("", "")
        params = request.GET.copy()
        params.pop("number", None)
        return render(
            request,
            "backend/mail/practical-reminder.html",
            {
                "mail_type": mail_type,
                "registration": registration,
                "subject": subject,
                "from_email": global_preferences_registry.manager()["email__FROM_MAIL"],
                "body": body,
                "is_html": mail_type.is_html if mail_type else False,
                "total": total,
                "number": number,
                "base_query": params.urlencode(),
                "previous": number - 1 if number > 1 else None,
                "next": number + 1 if number < total else None,
            },
        )

    def post(self, request):
        mail_type = self.mail_type()
        registrations = list(self.registrations(request))
        if not mail_type or not registrations:
            messages.error(request, "Installez le mail type et sélectionnez des cours avec des inscrits.")
            return redirect(request.get_full_path())
        preferences = global_preferences_registry.manager()
        schema = connection.schema_name
        with transaction.atomic():
            for registration in registrations:
                subject, body = self.mail_content(request, mail_type, registration)
                archive = MailArchive.objects.create(
                    subject=subject,
                    recipients=[registration.child.family.email],
                    bcc_recipients=[],
                    messages=[body],
                    template=BODY_TEMPLATE,
                    status=MailArchive.STATUS.draft,
                    is_html=mail_type.is_html,
                )
                transaction.on_commit(
                    lambda pk=archive.pk: send_practical_reminder.delay(
                        pk, schema, preferences["email__FROM_MAIL"], preferences["email__REPLY_TO_MAIL"]
                    )
                )
        messages.success(request, f"{len(registrations)} rappels mis en file d’envoi.")
        return redirect("backend:course-list")
