import collections
import functools
import json
import os
import re
from tempfile import mkdtemp

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import UpdateView
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin

from absences.models import Absence
from absences.models import Session
from absences.utils import closest_session
from absences.views import CourseAbsenceView
from activities.forms import CourseForm
from activities.forms import ExplicitDatesCourseForm
from activities.forms import PaySlipForm
from activities.models import Activity
from activities.models import Course
from activities.models import ExtraNeed
from activities.resources import CourseResource
from profiles.models import FamilyUser
from registrations.models import ChildActivityLevel
from registrations.models import ExtraInfo
from registrations.models import Registration
from registrations.resources import RegistrationResource
from sportfac.views import CSVMixin
from waiting_slots.forms import WaitingSlotForm

from ..forms import SessionForm
from ..utils import AbsencesPDFRenderer
from .mixins import BackendMixin
from .mixins import ExcelResponseMixin


LEVEL_RE = re.compile(r"^(\d+)([A-Za-z]*)$")


def parse_level(value: str):
    if not value:
        return (float("inf"), "")
    match = LEVEL_RE.match(value)
    if not match:
        return (float("inf"), value)
    number, suffix = match.groups()
    return int(number), suffix


class CourseMixin(BackendMixin):
    model = Course

    # noinspection PyUnresolvedReferences
    def get_queryset(self):
        user: FamilyUser = self.request.user
        if user.is_full_manager:
            return super().get_queryset()
        return super().get_queryset().filter(activity__in=user.managed_activities.all())


class CourseCreateView(SuccessMessageMixin, BackendMixin, CreateView):
    template_name = "backend/course/create.html"
    success_url = reverse_lazy("backend:course-list")
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been created.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["extra_needs"] = ExtraNeed.objects.all()
        return context

    def get_form_class(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            return ExplicitDatesCourseForm
        return CourseForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # noinspection PyUnresolvedReferences
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})

    def get_initial(self):
        initial = super().get_initial()
        activity = self.request.GET.get("activity", None)
        if activity:
            activity_obj = get_object_or_404(Activity, pk=activity)
            initial["activity"] = activity_obj

        if self.request.GET.get("source"):
            try:
                source = Course.objects.get(pk=self.request.GET.get("source"))
                initial.update(model_to_dict(source))
                del initial["number"]
                initial["uptodate"] = False
            except Course.DoesNotExist:
                pass
        return initial

    def form_valid(self, form):
        self.object = form.save()
        for extra in form.cleaned_data["extra"]:
            self.object.extra.add(extra)
        for city in form.cleaned_data.get("local_city_override", []):
            self.object.local_city_override.add(city)
        return HttpResponseRedirect(self.get_success_url())


class CourseDeleteView(SuccessMessageMixin, CourseMixin, DeleteView):
    template_name = "backend/course/confirm_delete.html"
    success_url = reverse_lazy("backend:course-list")
    success_message = _("Course has been deleted.")
    pk_url_kwarg = "course"

    def delete(self, request, *args, **kwargs):
        identifier = self.get_object().short_name
        messages.success(self.request, _("Course %(identifier)s has been deleted.") % {"identifier": identifier})
        return super().delete(request, *args, **kwargs)


class CourseDetailView(CourseMixin, DetailView):
    template_name = "backend/course/detail.html"
    pk_url_kwarg = "course"
    queryset = Course.objects.select_related("activity").prefetch_related(
        "participants__child__school_year",
        "participants__child__family",
        "participants__child__school",
        "participants__extra_infos",
        "instructors",
        "extra",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = context["object"]

        registrations = course.participants.all()
        context["registrations"] = registrations
        context["waiting_list_form"] = WaitingSlotForm(initial={"course": course})
        if settings.KEPCHUP_ENABLE_WAITING_LISTS:
            context["waiting_slots"] = course.waiting_slots.select_related("child", "child__family")
        return context


class CourseUpdateView(SuccessMessageMixin, CourseMixin, UpdateView):
    template_name = "backend/course/update.html"
    pk_url_kwarg = "course"
    success_url = reverse_lazy("backend:course-list")
    success_message = _('<a href="%(url)s" class="alert-link">Course (%(number)s)</a> has been updated.')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["extra_needs"] = ExtraNeed.objects.all()
        return context

    def get_form_class(self):
        if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
            return ExplicitDatesCourseForm
        return CourseForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # noinspection PyUnresolvedReferences
        kwargs["user"] = self.request.user
        return kwargs

    def get_success_message(self, cleaned_data):
        url = self.object.get_backend_url()
        return mark_safe(self.success_message % {"url": url, "number": self.object.number})

    def get_initial(self):
        initial = super().get_initial()
        initial["extra"] = self.get_object().extra.all()
        return initial

    def form_valid(self, form):
        course = self.get_object()
        response = super().form_valid(form)
        removed_extras = set(course.extra.all()) - set(form.cleaned_data["extra"])
        for removed_extra in removed_extras:
            course.extra.remove(removed_extra)
        for extra in form.cleaned_data["extra"]:
            course.extra.add(extra)
        if "local_city_override" in form.cleaned_data:
            removed_cities = set(course.local_city_override.all()) - set(form.cleaned_data["local_city_override"])
            for removed_city in removed_cities:
                course.local_city_override.remove(removed_city)
            for city in form.cleaned_data["local_city_override"]:
                course.local_city_override.add(city)
        return response  # noqa: R504


class CoursesToggleVisibilityView(CourseMixin, ListView):
    def get_queryset(self):
        courses_pk = [int(pk) for pk in self.request.POST.getlist("c") if pk.isdigit()]
        return super().get_queryset().filter(pk__in=courses_pk)

    def post(self, *args, **kwargs):
        courses = self.get_queryset()
        for course in courses:
            course.visible = not course.visible
            course.save()
        messages.info(self.request, _("Courses visibility has been toggled, %s courses changed.") % courses.count())
        return HttpResponseRedirect(reverse("backend:course-list"))


class BackendCourseAbsenceView(CourseMixin, CourseAbsenceView):
    template_name = "backend/course/absences.html"
    pk_url_kwarg = "course"

    def post(self, *args, **kwargs):
        course = self.get_object()
        form = SessionForm(data=self.request.POST)
        if form.is_valid():
            # noinspection PyUnresolvedReferences
            if self.request.user in course.instructors.all():
                # noinspection PyUnresolvedReferences
                instructor = self.request.user
            else:
                instructor = None
            with transaction.atomic():
                session, created = Session.objects.get_or_create(
                    course=course,
                    date=form.cleaned_data["date"],
                    defaults={"instructor": instructor, "activity": course.activity},
                )
                session.fill_absences()
                if settings.KEPCHUP_EXPLICIT_SESSION_DATES:
                    session.update_courses_dates()
                if created:
                    messages.success(
                        self.request,
                        _("Session %s has been added.") % session.date.strftime("%d.%m.%Y"),
                    )

        return HttpResponseRedirect(course.get_backend_absences_url())


class CoursesAbsenceView(CourseMixin, ListView):
    template_name = "backend/course/multiple-absences.html"

    # ------------------------------------------------------------
    # Ordering helpers
    # ------------------------------------------------------------

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
            "child.before_level",
            "child.after_level",
            "child.announced_level",
        }

        clean = []
        for column, direction in parsed:
            if column in allowed and direction in ("asc", "desc"):
                clean.append((column, direction))
        return clean

    def _sort_registrations(self, registrations, ordering):
        if not ordering:
            return registrations

        def cast_value(attr_path: str, reg):
            # Special case: numeric sort for bib_number
            if attr_path == "child.bib_number":
                try:
                    return int(reg.child.bib_number)
                except (TypeError, ValueError):
                    return float("inf")

            # Default: resolve attribute path dynamically
            return (
                functools.reduce(
                    lambda obj, attr: getattr(obj, attr, ""),
                    attr_path.split("."),
                    reg,
                )
                or ""
            )

        # Apply stable multi-column sort (rightmost key first)
        for attr_path, direction in reversed(ordering):
            registrations.sort(
                key=lambda reg: cast_value(attr_path, reg),
                reverse=(direction == "desc"),
            )

        return registrations

    # ------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------

    def get_queryset(self):
        courses_pk = [int(pk) for pk in self.request.GET.getlist("c") if pk.isdigit()]
        return super().get_queryset().filter(pk__in=courses_pk)

    def _get_registrations(self):
        return list(
            Registration.objects.filter(course__in=self.get_queryset()).select_related(
                "child",
                "course",
            )
        )

    def _inject_levels(self, registrations):
        if not settings.KEPCHUP_REGISTRATION_LEVELS:
            return

        # announced_level (ExtraInfo)
        extras = ExtraInfo.objects.select_related("registration", "key").filter(
            registration__course__in=self.get_queryset(),
            key__question_label__startswith="Niveau",
        )

        announced_levels = {extra.registration.child: extra.value for extra in extras}

        # before / after level (ChildActivityLevel)
        levels = ChildActivityLevel.objects.select_related("child").filter(
            activity__in={reg.course.activity for reg in registrations}
        )

        child_levels = {level.child: level for level in levels}

        for reg in registrations:
            child = reg.child
            child.announced_level = announced_levels.get(child, "")
            level = child_levels.get(child)
            child.before_level = getattr(level, "before_level", "")
            child.after_level = getattr(level, "after_level", "")

    def _get_absences_index(self):
        absences = Absence.objects.filter(session__course__in=self.get_queryset()).select_related(
            "child",
            "session",
            "session__course",
        )

        index = collections.defaultdict(dict)

        for absence in absences:
            key = (absence.child_id, absence.session.course_id)
            index[key][absence.session.date] = absence

        return index

    # ------------------------------------------------------------
    # Context
    # ------------------------------------------------------------

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        ordering = self._parse_order_from_request()

        registrations = self._get_registrations()
        self._inject_levels(registrations)
        registrations = self._sort_registrations(registrations, ordering)

        absences_index = self._get_absences_index()

        course_absences = collections.OrderedDict()
        for reg in registrations:
            key = (reg.child_id, reg.course_id)
            course_absences[key] = absences_index.get(key, {})

        sessions = Session.objects.filter(course__in=self.get_queryset())

        context["all_dates"] = sorted(
            set(sessions.values_list("date", flat=True)),
            reverse=not settings.KEPCHUP_ABSENCES_ORDER_ASC,
        )
        context["closest_session"] = closest_session(sessions)
        context["course_absences"] = course_absences
        context["levels"] = ChildActivityLevel.LEVELS
        context["session_form"] = SessionForm()

        return context

    # ------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------

    def get(self, request, *args, **kwargs):
        if "pdf" in self.request.GET:
            self.object_list = self.get_queryset()
            context = self.get_context_data()

            renderer = AbsencesPDFRenderer(context, self.request)
            tempdir = mkdtemp()

            filename = "absences-{}.pdf".format(
                "-".join(slugify(nb) for nb in self.object_list.values_list("number", flat=True))
            )
            if len(filename) > 100:
                filename = "absences.pdf"

            filepath = os.path.join(tempdir, filename)

            renderer.render_to_pdf(filepath)

            with open(filepath, "rb") as f:
                response = HttpResponse(
                    f.read(),
                    content_type="application/pdf",
                )

            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        return super().get(request, *args, **kwargs)


class CourseJSCSVView(CSVMixin, CourseDetailView):
    def get_csv_filename(self):
        return "%s - J+S.csv" % self.object.number

    def write_csv(self, filelike):
        return self.object.get_js_csv(filelike)


class CourseParticipantsView(CourseDetailView):
    template_name = "mailer/pdf_participants_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = list(range(0, self.object.number_of_sessions))
        return context

    def get_template_names(self):
        return self.template_name


class CourseListView(CourseMixin, ListView):
    queryset = Course.objects.select_related("activity").prefetch_related("participants", "instructors")
    template_name = "backend/course/list.html"


class CoursesExportView(BackendMixin, ExcelResponseMixin, View):
    filename = _("courses")
    model = Course

    def get_resource(self):
        return CourseResource()

    def get(self, request, *args, **kwargs):
        return self.render_to_response()


class CourseParticipantsExportView(SingleObjectMixin, CourseMixin, ExcelResponseMixin, View):
    pk_url_kwarg = "course"
    model = Course

    def get_filename(self):
        return self.object.number

    def get_resource(self):
        return RegistrationResource(course=self.object)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response()


class PaySlipMontreux(BackendMixin, CreateView):
    template_name = "backend/course/pay-slip-montreux-form.html"
    form_class = PaySlipForm

    def get_initial(self):
        user: FamilyUser = self.request.user
        if user.is_full_manager:
            course = get_object_or_404(Course, pk=self.kwargs["course"])
        else:
            course = get_object_or_404(Course, pk=self.kwargs["course"], activity__in=user.managed_activities.all())
        session_dates = course.sessions.values_list("date", flat=True)
        initial = {}
        instructor = get_object_or_404(FamilyUser, pk=self.kwargs["instructor"])
        course = get_object_or_404(Course, pk=self.kwargs["course"])
        from activities.models import CoursesInstructors

        try:
            courses_instructor = CoursesInstructors.objects.get(course=course, instructor=instructor)
            function = courses_instructor.function
            if function:
                initial["function"] = f"{function.name} ({function.code})"
                initial["rate_mode"] = function.rate_mode
                initial["rate"] = function.rate

        except CoursesInstructors.DoesNotExist:
            initial["function"] = ""

        if session_dates:
            initial["start_date"] = min(session_dates)
            initial["end_date"] = max(session_dates)
        return initial

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        context = self.get_context_data(**kwargs)
        self.object.course = context["course"]
        self.object.instructor = context["instructor"]
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs["instructor"] = get_object_or_404(FamilyUser, pk=self.kwargs["instructor"])
        kwargs["course"] = get_object_or_404(Course, pk=self.kwargs["course"])
        return super().get_context_data(**kwargs)
