import collections
import functools
import json
import logging
import os
from tempfile import mkdtemp

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView

from absences.models import Absence
from absences.models import Session
from absences.utils import closest_session
from activities.forms import ActivityForm
from activities.models import Activity
from activities.models import Course
from activities.models import ExtraNeed
from profiles.models import FamilyUser as User
from registrations.models import ChildActivityLevel
from registrations.models import ExtraInfo

from ..forms import SessionForm
from ..utils import AbsencePDFRenderer
from .mixins import BackendMixin


logger = logging.getLogger(__name__)


class ActivityMixin:
    # noinspection PyUnresolvedReferences
    def get_queryset(self):
        user: User = self.request.user
        if user.is_full_manager:
            return super().get_queryset()
        return user.managed_activities.all()


class ActivityDetailView(BackendMixin, ActivityMixin, DetailView):
    model = Activity
    slug_field = "slug"
    slug_url_kwarg = "activity"
    template_name = "backend/activity/detail.html"


class ActivityListView(BackendMixin, ActivityMixin, ListView):
    model = Activity
    template_name = "backend/activity/list.html"


class ActivityCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    success_url = reverse_lazy("backend:activity-list")
    success_message = _('<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been created.')
    template_name = "backend/activity/create.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        user: User = self.request.user
        if user.is_restricted_manager:
            user.managed_activities.add(self.object)
            user.save()
        return response  # noqa: R504

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})


class ActivityAbsenceView(BackendMixin, ActivityMixin, DetailView):
    model = Activity
    template_name = "backend/activity/absences.html"
    slug_field = "slug"
    slug_url_kwarg = "activity"

    # ------------------------------------------------------------------
    # Ordering helpers
    # ------------------------------------------------------------------

    def _parse_order_from_request(self):
        order_param = self.request.GET.get("order")
        if not order_param:
            return []

        try:
            parsed = json.loads(order_param)
        except ValueError:
            return []

        allowed = {
            "child.last_name",
            "child.first_name",
            "child.ordering_name",
            "child.bib_number",
            "child.announced_level",
            "child.before_level",
            "child.after_level",
        }

        clean = []
        if not clean and parsed:
            logger.warning("Ignored ordering keys: %s", parsed)
        for column, direction in parsed:
            if column in allowed and direction in ("asc", "desc"):
                clean.append((column, direction))
        return clean

    def _sort_registrations(self, registrations, ordering):
        if not ordering:
            return registrations

        def cast_value(attr_path: str, value):
            if attr_path == "child.bib_number":
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return float("inf")
            return value or ""

        for attr_path, direction in reversed(ordering):
            registrations.sort(
                key=lambda reg: cast_value(
                    attr_path,
                    functools.reduce(
                        lambda obj, attr: getattr(obj, attr, ""),
                        attr_path.split("."),
                        reg,
                    ),
                ),
                reverse=(direction == "desc"),
            )

        return registrations

    def post(self, *args, **kwargs):
        activity = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            msg = []
            with transaction.atomic():
                for course in activity.courses.all():
                    session, created = Session.objects.get_or_create(
                        course=course,
                        date=form.cleaned_data["date"],
                        defaults={"activity": activity},
                    )
                    session.fill_absences()
                    if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                        session.update_courses_dates()
                    if created:
                        msg.append(
                            _("Session of %(date)s for %(course)s has been added.")
                            % {"date": session.date.strftime("%d.%m.%Y"), "course": course.number}
                        )
            messages.success(self.request, mark_safe("<br>".join(msg)))

        return HttpResponseRedirect(activity.backend_absences_url)

    def get_context_data(self, **kwargs):
        self.object = Activity.objects.prefetch_related("courses__instructors").get(pk=self.object.pk)
        context = super().get_context_data(**kwargs)
        # ------------------------------------------------------------
        # 1. Parse ordering coming from DataTables
        # ------------------------------------------------------------
        ordering = self._parse_order_from_request()
        # ------------------------------------------------------------
        # 2. Base querysets
        #    IMPORTANT: qs MUST NOT define display order
        # ------------------------------------------------------------
        qs = Absence.objects.select_related(
            "child",
            "session",
            "session__course",
        ).filter(session__activity=self.object)

        all_registrations = self.object.participants.select_related(
            "child",
            "course",
            "course__activity",
            "transport",
        )
        # ------------------------------------------------------------
        # 3. Course filtering (affects registrations, not order logic)
        # ------------------------------------------------------------
        if "c" in self.request.GET:
            courses_ids = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
            if len(courses_ids) == 1:
                try:
                    context["course"] = Course.objects.get(pk=courses_ids[0])
                except Course.DoesNotExist:
                    pass

            all_registrations = all_registrations.filter(course_id__in=courses_ids)

        elif self.object.courses.count() == 1:
            context["course"] = self.object.courses.first()
        # ------------------------------------------------------------
        # 4. qs ordering
        #    This ordering is ONLY for deterministic iteration,
        #    NOT for display ordering.
        # ------------------------------------------------------------
        qs = qs.order_by("child__last_name", "child__first_name")
        # ------------------------------------------------------------
        # 5. Sessions context
        # ------------------------------------------------------------
        if "course" in context:
            sessions = context["course"].sessions.all()
        else:
            sessions = self.object.sessions.all()
        sessions = sessions.select_related("course", "instructor").prefetch_related("course__instructors")

        context["sessions"] = {s.date: s for s in sessions}
        context["closest_session"] = closest_session(sessions)
        context["all_dates"] = sorted(
            (s.date for s in sessions),
            reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC,
        )

        # ------------------------------------------------------------
        # 6. Registrations ordering (THIS is the display order)
        # ------------------------------------------------------------
        registrations = list(all_registrations)
        registrations = self._sort_registrations(registrations, ordering)

        # ------------------------------------------------------------
        # 7. Index absences by child + date
        #    NO ordering logic here, pure lookup structure
        # ------------------------------------------------------------
        absences_by_child = collections.defaultdict(dict)

        for absence in qs:
            absences_by_child[absence.child][absence.session.date] = absence

        # ------------------------------------------------------------
        # 8. Build final OrderedDict following registrations order
        #    THIS is where order must be preserved
        # ------------------------------------------------------------
        child_absences = collections.OrderedDict()

        for reg in registrations:
            child = reg.child
            child_absences[(child, reg)] = absences_by_child.get(child, {})

        # ------------------------------------------------------------
        # 9. Remaining context
        # ------------------------------------------------------------
        context["session_form"] = SessionForm()
        context["child_absences"] = child_absences

        if settings.KEPCHUP_REGISTRATION_LEVELS:
            context["levels"] = ChildActivityLevel.LEVELS

            context["child_levels"] = {
                lvl.child: lvl
                for lvl in ChildActivityLevel.objects.filter(activity=self.object).select_related("child")
            }

            questions = ExtraNeed.objects.filter(question_label__startswith="Niveau")

            context["extras"] = {
                extra.registration.child: extra.value
                for extra in ExtraInfo.objects.filter(
                    registration__course__activity=self.object,
                    key__in=questions,
                ).select_related("registration__child")
            }

        return context

    def get(self, request, *args, **kwargs):
        if "pdf" in self.request.GET:
            self.object: Activity = self.get_object()
            context = self.get_context_data(object=self.object)
            renderer = AbsencePDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = f"absences-{slugify(self.object.number)}.pdf"
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            with open(filepath, "rb") as f:
                response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            return response
        return super().get(request, *args, **kwargs)


class ActivityUpdateView(SuccessMessageMixin, BackendMixin, ActivityMixin, UpdateView):
    model = Activity
    form_class = ActivityForm
    slug_field = "slug"
    slug_url_kwarg = "activity"
    success_url = reverse_lazy("backend:activity-list")
    success_message = _('<a href="%(url)s" class="alert-link">Activity (%(number)s)</a> has been updated.')
    template_name = "backend/activity/update.html"

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})


class ActivityDeleteView(SuccessMessageMixin, BackendMixin, ActivityMixin, DeleteView):
    model = Activity
    slug_field = "slug"
    slug_url_kwarg = "activity"
    success_message = _("Activity has been deleted.")
    success_url = reverse_lazy("backend:activity-list")
    template_name = "backend/activity/confirm_delete.html"

    def delete(self, request, *args, **kwargs):
        # noinspection PyAttributeOutsideInit
        self.object = self.get_object()
        identifier = self.get_object().number
        messages.success(
            self.request,
            _("Activity %(identifier)s has been deleted.") % {"identifier": identifier},
        )
        return super().delete(request, *args, **kwargs)
