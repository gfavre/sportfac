import collections
import json
import os
from tempfile import mkdtemp

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.text import slugify
from django.views.generic import DetailView

from activities.models import Course, ExtraNeed
from activities.views import InstructorMixin
from backend.forms import SessionForm  # TODO move sessionform to a more appropriate place
from backend.utils import AbsencePDFRenderer  # TODO move pdfrenderer to a more appropriate place
from registrations.models import ChildActivityLevel, ExtraInfo

from .models import Absence, Session
from .utils import closest_session


class CourseAbsenceView(DetailView):
    model = Course
    template_name = "backend/course/absences.html"
    pk_url_kwarg = "course"
    queryset = Course.objects.prefetch_related(
        "sessions", "sessions__absences", "participants__child", "instructors"
    ).select_related(
        "activity",
    )

    def get_sorted_registrations(self, registrations_list):
        ordering = json.loads(self.request.GET.get("order", "[]"))
        if not ordering:
            return registrations_list

        def sort_key(registration):
            values = []
            for attr_path, _order in ordering:
                # Split the attribute path and fetch the attribute value
                attr_obj = registration
                for attr in attr_path.split("."):
                    try:
                        attr_obj = getattr(attr_obj, attr)
                    except AttributeError:
                        attr_obj = ""
                # Append or prepend the value based on sort order
                values.append(attr_obj)
            return tuple(values)

        registrations_list.sort(key=sort_key, reverse=ordering[0][1] == "desc")
        return registrations_list

    def get_child_absences(self):
        # 1. Get all extra infos for this course
        registrations = list(self.object.participants.all())
        announced_levels = ExtraInfo.objects.filter(
            key__question_label__startswith="Niveau", registration__course__activity=self.object.activity
        )
        levels = {level.child: level for level in ChildActivityLevel.objects.filter(activity=self.object.activity)}
        children_announced_levels = {extra_info.registration.child: extra_info for extra_info in announced_levels}

        # 2. Enrich children to be able to sort without recalculating related fields
        for registration in registrations:
            announced_level = children_announced_levels.get(registration.child, None)
            if announced_level:
                announced_level = announced_level.value
            registration.child.announced_level = announced_level or ""
            level = levels.get(registration.child, None)
            before_level = after_level = note = ""
            if level:
                before_level = level.before_level
                after_level = level.after_level
                note = level.note
            registration.child.before_level = before_level
            registration.child.after_level = after_level
            registration.child.note = note

        # 3. Add absences to children
        child_absences = collections.OrderedDict()

        for registration in self.get_sorted_registrations(registrations):
            child_absences[(registration.child, registration)] = {}

        qs = Absence.objects.select_related("child", "session").filter(session__course=self.object)
        if settings.KEPCHUP_BIB_NUMBERS:
            qs = qs.order_by("child__bib_number", "child__last_name", "child__first_name")
        else:
            qs = qs.order_by("child__last_name", "child__first_name")

        for absence in qs:
            child = absence.child
            if child not in registrations:
                # happens if child was previously attending this course but is no longer
                continue
            registration = registrations[child]

            the_tuple = (child, registration)
            if the_tuple in child_absences:
                child_absences[the_tuple][absence.session.date] = absence
            else:
                child_absences[the_tuple] = {absence.session.date: absence}
        return child_absences

    def get_context_data(self, **kwargs):
        sessions = self.object.sessions.all()
        kwargs["sessions"] = {session.date: session for session in sessions}
        kwargs["closest_session"] = closest_session(sessions)
        kwargs["all_dates"] = sorted(
            kwargs["sessions"].keys(),
            reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC,
        )
        child_absences = self.get_child_absences()
        kwargs["session_form"] = SessionForm()
        kwargs["child_absences"] = child_absences
        kwargs["courses_list"] = Course.objects.select_related("activity")
        if settings.KEPCHUP_REGISTRATION_LEVELS:
            kwargs["levels"] = ChildActivityLevel.LEVELS
            kwargs["child_levels"] = {
                lvl.child: lvl
                for lvl in ChildActivityLevel.objects.filter(activity=self.object.activity).select_related("child")
            }
            try:
                questions = ExtraNeed.objects.filter(question_label__startswith="Niveau")
                all_extras = {
                    extra.registration.child: extra.value
                    for extra in ExtraInfo.objects.filter(
                        registration__course=self.object, key__in=questions
                    ).select_related("registration__child")
                }
            except ExtraNeed.DoesNotExist:
                all_extras = {}
            kwargs["extras"] = all_extras
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        if "pdf" in self.request.GET:
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            renderer = AbsencePDFRenderer(context, self.request)
            tempdir = mkdtemp()
            filename = f"absences-{slugify(self.object.number)}.pdf"
            filepath = os.path.join(tempdir, filename)
            renderer.render_to_pdf(filepath)
            with open(filepath, "rb") as f:
                response = HttpResponse(f.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        return super().get(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            with transaction.atomic():
                # noinspection PyUnresolvedReferences
                session, created = Session.objects.get_or_create(
                    course=course,
                    date=form.cleaned_data["date"],
                    defaults={"instructor": self.request.user, "activity": course.activity},
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
