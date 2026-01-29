import collections
import json
import os
from tempfile import mkdtemp

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.utils.text import slugify
from django.views.generic import DetailView

from activities.models import Course
from activities.models import ExtraNeed
from activities.views import InstructorMixin
from backend.forms import SessionForm  # TODO move sessionform to a more appropriate place
from backend.utils import AbsencePDFRenderer  # TODO move pdfrenderer to a more appropriate place
from registrations.models import ChildActivityLevel
from registrations.models import ExtraInfo

from .models import Absence
from .models import Session
from .utils import closest_session


class CourseAbsenceView(DetailView):
    model = Course
    template_name = "backend/course/absences.html"
    pk_url_kwarg = "course"
    queryset = Course.objects.prefetch_related(
        "sessions", "sessions__absences", "participants__child", "instructors"
    ).select_related("activity")

    # ---------------------------------------------------------------------
    # Ordering helpers
    # ---------------------------------------------------------------------

    def _parse_order_from_request(self):
        order_param = self.request.GET.get("order")
        if not order_param:
            return []

        try:
            parsed = json.loads(order_param)
        except ValueError:
            return []

        # security: only allow known attributes
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
        for column, direction in parsed:
            if column in allowed and direction in ("asc", "desc"):
                clean.append((column, direction))
        return clean

    def _sort_registrations(self, registrations, ordering):
        if not ordering:
            return registrations

        def sort_key(reg):
            values = []
            for attr_path, _direction in ordering:
                obj = reg
                for attr in attr_path.split("."):
                    obj = getattr(obj, attr, "")
                if attr_path == "child.bib_number":
                    try:
                        obj = int(obj)
                    except (TypeError, ValueError):
                        obj = float("inf")  # push empty / invalid to the end
                values.append(obj)
            return tuple(values)

        reverse = ordering[0][1] == "desc"
        registrations.sort(key=sort_key, reverse=reverse)
        return registrations

    # ---------------------------------------------------------------------
    # Core data
    # ---------------------------------------------------------------------

    def get_child_absences(self, ordering):
        registrations = list(self.object.participants.all())

        # Levels / extras enrichment (unchanged logic)
        announced_levels = ExtraInfo.objects.filter(
            key__question_label__startswith="Niveau",
            registration__course__activity=self.object.activity,
        )
        levels = {lvl.child: lvl for lvl in ChildActivityLevel.objects.filter(activity=self.object.activity)}
        announced = {extra.registration.child: extra.value for extra in announced_levels}

        for reg in registrations:
            child = reg.child
            child.announced_level = announced.get(child, "")
            level = levels.get(child)
            child.before_level = level.before_level if level else ""
            child.after_level = level.after_level if level else ""
            child.note = level.note if level else ""

        registrations = self._sort_registrations(registrations, ordering)

        child_absences = collections.OrderedDict(((reg.child, reg), {}) for reg in registrations)

        qs = Absence.objects.select_related("child", "session").filter(session__course=self.object)

        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by("child__bib_number", "child__last_name", "child__first_name")
        else:
            qs = qs.order_by("child__last_name", "child__first_name")

        attendees = {reg.child: reg for reg in registrations}

        for absence in qs:
            child = absence.child
            if child not in attendees:
                continue
            reg = attendees[child]
            child_absences[(child, reg)][absence.session.date] = absence

        return child_absences

    # ---------------------------------------------------------------------
    # Context
    # ---------------------------------------------------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ordering = self._parse_order_from_request()
        sessions = self.object.sessions.all()

        context.update(
            {
                "sessions": {s.date: s for s in sessions},
                "closest_session": closest_session(sessions),
                "all_dates": sorted(
                    (s.date for s in sessions),
                    reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC,
                ),
                "session_form": SessionForm(),
                "child_absences": self.get_child_absences(ordering),
                "courses_list": Course.objects.select_related("activity"),
            }
        )

        if settings.KEPCHUP_REGISTRATION_LEVELS:
            context["levels"] = ChildActivityLevel.LEVELS
            context["child_levels"] = {
                lvl.child: lvl
                for lvl in ChildActivityLevel.objects.filter(activity=self.object.activity).select_related("child")
            }

            questions = ExtraNeed.objects.filter(question_label__startswith="Niveau")
            context["extras"] = {
                extra.registration.child: extra.value
                for extra in ExtraInfo.objects.filter(
                    registration__course=self.object, key__in=questions
                ).select_related("registration__child")
            }

        return context

    # ---------------------------------------------------------------------
    # PDF
    # ---------------------------------------------------------------------

    def get(self, request, *args, **kwargs):
        if "pdf" in request.GET:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)

            renderer = AbsencePDFRenderer(context, request)
            tempdir = mkdtemp()
            filename = f"absences-{slugify(self.object.number)}.pdf"
            filepath = os.path.join(tempdir, filename)

            renderer.render_to_pdf(filepath)

            with open(filepath, "rb") as f:
                response = HttpResponse(f.read(), content_type="application/pdf")

            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        return super().get(request, *args, **kwargs)

    # ---------------------------------------------------------------------
    # POST (unchanged)
    # ---------------------------------------------------------------------

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            with transaction.atomic():
                session, _ = Session.objects.get_or_create(
                    course=course,
                    date=form.cleaned_data["date"],
                    defaults={
                        "instructor": self.request.user,
                        "activity": course.activity,
                    },
                )
                session.fill_absences()
                if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                    course.update_dates_from_sessions()
        return HttpResponseRedirect(course.get_absences_url())


class AbsenceCourseView(InstructorMixin, CourseAbsenceView):
    template_name = "absences/absences.html"
    pk_url_kwarg = "course"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["session_form"] = SessionForm()
        # noinspection PyUnresolvedReferences
        kwargs["courses_list"] = self.request.user.course.prefetch_related("activity")
        return context
